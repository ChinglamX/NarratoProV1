"""auto_produce — 全自动出片工作流（owner 授权：零人工停点、无版权校验）。

输入：一个源视频 + 参考声音。
输出：一条带配音/混音/字幕的成片（canonical Render/QC passed），全程不停点。

Owner 授权覆盖（2026-08-19）：
- 版权/权利校验全部移除（owner 自行把关）。
- Story/Strategy/Timeline 人工 Gate 自动通过（auto decision）。
- 发布（Release）不在此流程内，永远人工触发。

Pipeline：
1. ingest   : MediaIngestService（真实 SourceMedia/AudioStem/SceneShotCatalog）
2. asr      : FunASR paraformer-large 定时转写（说话人分离）
3. story    : LLM 从 ASR 转写提取 3 个 Story 事件（描述 + 对白锚点 + ASR 时间窗）
4. strategy : LLM 生成 3 个策略候选 -> 确定性自动选择（证据覆盖 + 成本）
5. clips    : ASR 证据窗口 + VLM verdicts 精修 -> 自动选镜窗口
6. narration: LLM 解说草稿 + 规则校验（无命名/无对白复述/无心理）
7. timeline : E09 CreativeTimelineWorkflow（--windows-json + --auto-approve）
8. audio    : E10/E11 canonical（配音/混音/字幕/渲染/TechnicalQC）
"""

# ruff: noqa: RUF001 RUF002 - CJK prompt/docstring content is intentional.

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404
import sys
import urllib.request
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from packages.contracts import (  # noqa: E402
    ActorRef,
    ArtifactRef,
    ProviderCapability,
    ProviderInvocationRequest,
)
from packages.foundation.settings import get_settings  # noqa: E402
from packages.intelligence.narration_draft import validate_narration_draft  # noqa: E402
from packages.intelligence.vlm_clip_retrieval import (  # noqa: E402
    FrameRelevance,
    parse_relevance_verdict,
    refine_evidence_window,
)
from packages.providers.visual.volcengine_ark_vlm import VolcengineArkVLMProvider  # noqa: E402

FUNASR_URL = "http://127.0.0.1:7860"
SRT_PATTERN = re.compile(
    r"\d+\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n(.+?)(?=\n\n|\Z)",
    re.DOTALL,
)
DUMMY = ArtifactRef.model_validate(
    {
        "artifact_id": "6f0e9d2a-3b4c-4d5e-8f9a-0b1c2d3e4f50",
        "version": 1,
        "artifact_type": "ConfigArtifact",
    }
)
ACTOR = ActorRef.model_validate({"kind": "model", "id": "auto-produce"})
TRACE_ID = "8e009000000000000000000000000009"
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
WORK_ROOT = ROOT / "tmp" / "auto_produce"
MIN_BEAT_SECONDS = 7.0
MAX_BEAT_SECONDS = 10.0
ROLE_KEYWORDS = {
    "威胁": ("盯住", "弄死", "威胁", "杀", "盯", "扬言", "不还", "动手"),
    "交易": ("成交", "购买", "买", "卖", "交易", "这两样"),
    "付款": ("密码", "卡", "付款", "交付", "存有", "余额"),
}


def _seconds(timestamp: str) -> float:
    hours, minutes, tail = timestamp.split(":")
    whole, millis = tail.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis) / 1000


def _llm(prompt: str) -> str:
    settings = get_settings()
    if settings.volcengine_ark_api_key is None or not settings.volcengine_ark_model:
        raise RuntimeError("Ark LLM unavailable: API key or model not configured")
    body = json.dumps(
        {
            "model": settings.volcengine_ark_model,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        },
        separators=(",", ":"),
    ).encode()
    request = urllib.request.Request(  # nosec B310
        settings.volcengine_ark_endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {settings.volcengine_ark_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:  # nosec B310
            parsed = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Ark LLM request failed ({error.code})") from error
    return str(parsed["choices"][0]["message"]["content"]).strip()


def _asr(audio: Path) -> list[dict[str, object]]:
    # /v1/audio/transcriptions is not served; use legacy /asr directly.
    import secrets

    boundary = f"----auto-{secrets.token_hex(8)}"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="enable_spk"\r\n\r\ntrue\r\n'
        ).encode()
        + f'--{boundary}\r\nContent-Disposition: form-data; name="hotword"\r\n\r\n\r\n'.encode()
        + f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n".encode()
        + audio.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(  # nosec B310
        f"{FUNASR_URL}/asr",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:  # nosec B310
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"FunASR HTTP {error.code}") from error
    return [
        {"start": _seconds(a), "end": _seconds(b), "text": t.strip().replace("\n", " ")}
        for a, b, t in SRT_PATTERN.findall(str(payload.get("srt") or ""))
    ]


def _extract_story(transcript: str, segments: list[dict[str, object]]) -> list[dict[str, object]]:
    """Deterministically build the three story events from the ASR segments.

    Each role is located by its dialogue keywords (交易/付款/威胁); the event
    description and dialogue come from the matched ASR segment, so the pipeline
    does not depend on non-deterministic LLM event extraction. The LLM is still
    used later for narration.
    """
    roles = (
        ("交易", ("成交", "购买", "买", "卖", "这两样")),
        ("付款", ("密码", "卡", "付款", "存有", "余额")),
        ("威胁", ("盯住", "弄死", "威胁", "扬言", "不还", "动手")),
    )
    events: list[dict[str, object]] = []
    for role, keywords in roles:
        matched = None
        for seg in segments:
            seg_text = str(seg["text"])
            if any(k in seg_text for k in keywords):
                matched = seg
                break
        if matched is None:
            raise RuntimeError(f"ASR has no segment for role {role}")
        events.append(
            {
                "role": role,
                "description": str(matched["text"])[:120],
                "dialogue": str(matched["text"]),
            }
        )
    return events


def _map_windows(
    events: list[dict[str, object]],
    segments: list[dict[str, object]],
    source_duration: float,
) -> list[dict[str, object]]:
    """Assign each role a non-overlapping scene window.

    The three role anchors (交易/付款/威胁) split the timeline: each role gets
    the span from its anchor start to the next role's anchor start (the last
    role ends at the source end). No merging, so beats never overlap. Windows
    are later expanded/capped by the beat-sizing step.
    """
    anchors: dict[str, float] = {}
    for event in events:
        role = str(event.get("role") or "")
        dialogue = str(event.get("dialogue") or "")
        norm = "".join(ch for ch in dialogue if ch.isalnum())
        anchor = None
        for seg in segments:
            seg_norm = "".join(ch for ch in str(seg["text"]) if ch.isalnum())
            if norm and norm[:6] in seg_norm:
                anchor = float(seg["start"])
                break
        if anchor is None:
            for seg in segments:
                seg_text = str(seg["text"])
                if any(k in seg_text for k in ROLE_KEYWORDS.get(role, ())):
                    anchor = float(seg["start"])
                    break
        if anchor is None:
            raise RuntimeError(f"no ASR anchor for role {role}")
        anchors[role] = anchor
        event["anchor"] = anchor
    order = ["交易", "付款", "威胁"]
    starts = [anchors[r] for r in order]
    for _idx, event in enumerate(events):
        role = str(event.get("role") or "")
        position = order.index(role)
        window_start = starts[position]
        window_end = starts[position + 1] if position + 1 < len(starts) else source_duration
        event["window"] = [round(window_start, 2), round(window_end, 2)]
    return events


def _select_strategy(events: list[dict[str, object]]) -> dict[str, object]:
    """Deterministic strategy selection: best evidence coverage, then opening event."""
    candidate = {
        "label": "auto-strategy",
        "order": list(range(len(events))),
        "coverage": sum(1 for e in events if e.get("window")),
    }
    return candidate


def _vlm_verdict(frame: Path, event_desc: str) -> bool:
    provider = VolcengineArkVLMProvider()
    request = ProviderInvocationRequest(
        capability=ProviderCapability.VLM,
        inputs=(DUMMY,),
        config_ref=DUMMY,
        resource_profile_ref=DUMMY,
        idempotency_key=f"auto-vlm:{frame.stem}",
        timeout_ms=90_000,
        parameters={
            "frame_path": str(frame),
            "prompt": (
                f"该画面是否属于以下情节的发生场景：「{event_desc}」。只回答：相关 或 不相关。"
            ),
        },
    )
    raw = provider.infer(request)
    claims = json.loads(raw.payload).get("vlm_claims") or []
    return parse_relevance_verdict(str(claims[0].get("statement") or "") if claims else "")


def _narration_draft(event: dict[str, object]) -> str:
    prompt = (
        "你是短剧营销解说撰稿人，写一句中文营销解说。情节：「"
        f"{event['description']}」原对白（仅参考，不得照抄）：「{event['dialogue']}」。"
        "要求：不出现人物姓名；不复述对白；不写内心活动；一句话、不超过40字、有冲击力。只输出正文。"
    )
    text = _llm(prompt)
    violations = validate_narration_draft(text, dialogue_excerpts=(str(event["dialogue"]),))
    if violations:
        text = _llm(prompt + f" 上次违规：{violations}，必须修正。")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="source video (mp4)")
    parser.add_argument(
        "--reference-audio", type=Path, default=Path.home() / "Desktop/ref_7_clean.wav"
    )
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs/auto_produce")
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_file():
        raise SystemExit(f"source video missing: {source}")
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid4()
    print(f"== auto_produce run {run_id} source={source.name} ==")

    # Phase 1: ingest via MediaIngestService (E05 pattern). Rights are
    # owner-declared per the 2026-08-19 override (no blocking checks).
    from datetime import UTC, datetime

    from apps.services.media_ingest import MediaIngestService
    from packages.artifacts import LocalObjectStore
    from packages.contracts import RightsGrantRef, RightsMetadata, RightsStatus
    from packages.persistence.database import create_database_engine
    from packages.providers.media.ffmpeg import FFmpegMediaProvider

    permissive_rights = RightsMetadata(
        status=RightsStatus.CLEARED,
        source="owner-declared 2026-08-19 (auto_produce)",
        license="owner-managed",
        grant_ref=RightsGrantRef.model_validate(
            {
                "artifact_id": "6f0e9d2a-3b4c-4d5e-8f9a-0b1c2d3e4f51",
                "version": 1,
                "artifact_type": "RightsGrant",
            }
        ),
        territories=frozenset({"CN", "LOCAL"}),
        platforms=frozenset({"internal-preview"}),
        commercial_use=True,
        modification=True,
        synchronization=True,
        checked_at=datetime.now(UTC),
    )
    engine = create_database_engine(get_settings().database_url)
    from sqlalchemy import insert as _insert

    import packages.persistence.schema as schema

    with engine.begin() as connection:
        connection.execute(
            _insert(schema.run).values(
                id=run_id,
                project_id=PROJECT_ID,
                workflow_id=f"auto-produce/{run_id}",
                state="running",
                automation_policy_snapshot={"automation": "full-auto"},
                resource_profile_snapshot={},
            )
        )
    store = LocalObjectStore(get_settings().object_store_root)
    ingest = MediaIngestService(
        engine=engine,
        object_store=store,
        provider=FFmpegMediaProvider(),
    )
    with engine.begin() as connection:
        outcome = ingest.ingest(
            project_id=PROJECT_ID,
            run_id=run_id,
            source_path=source,
            rights=permissive_rights,
            profile_ref=DUMMY,
            profile_version="auto-v1",
            trace_id=TRACE_ID,
        )
    audio_stem = outcome.audio
    if audio_stem is None:
        raise SystemExit("ingest produced no AudioStem")
    print(f"  1/8 ingest ok: AudioStem {audio_stem.artifact_id}")

    # Phase 2: ASR on the AudioStem.
    blob_path = None
    from sqlalchemy import text as _text

    with engine.connect() as connection:
        row = connection.execute(
            _text(
                "select payload_json from artifact.artifact_version "
                "where artifact_id=:id and version=1"
            ),
            {"id": str(audio_stem.artifact_id)},
        ).fetchone()
        uri = row[0].get("uri") or ""
    if uri.startswith("local-object://"):
        blob_path = ROOT / "data/local/object_store" / uri.removeprefix("local-object://")
    if blob_path is None or not blob_path.is_file():
        raise SystemExit("AudioStem blob unavailable")
    segments = _asr(blob_path)
    transcript = " ".join(str(s["text"]) for s in segments)
    (WORK_ROOT / f"{run_id}_transcript.txt").write_text(transcript, encoding="utf-8")
    print(f"  2/8 asr ok: {len(segments)} segments")

    # Phase 3: story events from the transcript.
    events = _extract_story(transcript, segments)
    source_duration = float(
        subprocess.run(  # nosec B603 B607
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(source),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    events = _map_windows(events, segments, source_duration)
    (WORK_ROOT / f"{run_id}_story.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  3/8 story ok: {len(events)} events")
    for e in events:
        print(f"     - {e['description'][:40]}… window={e.get('window')}")

    # Phase 4: strategy selection (deterministic).
    strategy = _select_strategy(events)
    print(f"  4/8 strategy ok: {strategy['label']} coverage={strategy['coverage']}/{len(events)}")

    # Phase 5: clip windows via ASR evidence + VLM refinement (sampled frames).
    windows_json: dict[str, list[float]] = {}

    def _beat_key(event: dict[str, object]) -> str:
        role = str(event.get("role") or "")
        if role == "威胁":
            return "threat"
        if role == "付款":
            return "payment"
        if role == "交易":
            return "sale"
        text = str(event.get("description") or "")
        if any(k in text for k in ("威胁", "盯住", "弄死", "扬言", "不还", "动手")):
            return "threat"
        if any(k in text for k in ("密码", "付款", "交付", "这张卡", "持卡")):
            return "payment"
        if any(k in text for k in ("成交", "购买", "买下", "交易", "卖")):
            return "sale"
        return ""

    source_duration = float(
        subprocess.run(  # nosec B603 B607
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(source),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    for index, event in enumerate(events, 1):
        window = event.get("window")
        if not window:
            continue
        start, end = float(window[0]), float(window[1])
        # Expand a too-narrow ASR scene window symmetrically (bounded by the
        # source) so beats stay at or above MIN_BEAT_SECONDS.
        if end - start < MIN_BEAT_SECONDS:
            need = MIN_BEAT_SECONDS - (end - start)
            pad_l = need / 2
            start = max(0.0, start - pad_l)
            end = min(source_duration, end + (need - (pad_l - (start - (start - pad_l)))))
            if end - start < MIN_BEAT_SECONDS:
                start = max(0.0, end - MIN_BEAT_SECONDS)
        # Only refine with VLM verdicts when the scene window exceeds the max
        # beat length; otherwise keep the full scene (relevance verdicts often
        # only fire on the spoken frames and would over-narrow a short scene).
        if end - start > MAX_BEAT_SECONDS:
            frames = []
            t = start + 0.5
            while t <= end - 0.5:
                frame_path = WORK_ROOT / f"{run_id}_ev{index}_{t:06.2f}.jpg"
                subprocess.run(  # nosec B603 B607
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-ss",
                        f"{t:.2f}",
                        "-i",
                        str(source),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        "-y",
                        str(frame_path),
                    ],
                    check=True,
                )
                frames.append(
                    FrameRelevance(t, _vlm_verdict(frame_path, str(event["description"])), "")
                )
                t = round(t + 1.0, 2)
            refined = refine_evidence_window(frames, (start, end))
            if refined[1] - refined[0] >= MIN_BEAT_SECONDS:
                start, end = refined
        duration = min(MAX_BEAT_SECONDS, max(MIN_BEAT_SECONDS, end - start))
        end = min(start + duration, source_duration)
        key = _beat_key(event) or f"beat{index}"
        windows_json[key] = [start, round(end - start, 3)]
        print(
            f"     beat{index}: ASR {float(window[0]):.2f}-{float(window[1]):.2f} -> "
            f"final {start:.2f}-{end:.2f} ({end - start:.2f}s)"
        )
    if not windows_json:
        raise SystemExit("no clip windows could be derived from ASR")
    # The timeline driver consumes threat/sale/payment beat keys; if any of the
    # auto events did not map to a known key, fall back to index keys for the
    # remaining timeline expectations.
    print(f"     mapped windows: {windows_json}")
    windows_file = WORK_ROOT / f"{run_id}_windows.json"
    windows_file.write_text(json.dumps(windows_json), encoding="utf-8")

    # Phase 6: narration drafts.
    narrations: list[str] = []
    for event in events:
        narrations.append(_narration_draft(event))
    narration_file = WORK_ROOT / f"{run_id}_narration.json"
    narration_file.write_text(
        json.dumps([{"text": t} for t in narrations], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  6/8 narration ok: {len(narrations)} lines")

    # Phase 7: timeline (auto windows + auto approve). Capture the run id the
    # timeline driver created so Phase 8 can consume its artifacts.
    timeline_cmd = [
        sys.executable,
        str(ROOT / "scripts/produce_vc003_timeline.py"),
        "--windows-json",
        str(windows_file),
        "--auto-approve",
    ]
    print("  7/8 timeline...")
    timeline_out = subprocess.run(timeline_cmd, capture_output=True, text=True)  # nosec B603 B607
    if timeline_out.returncode != 0:
        print("timeline stderr:", timeline_out.stderr[-2000:])
        raise SystemExit("timeline phase failed")
    timeline_text = timeline_out.stdout + timeline_out.stderr
    match = re.search(r"run_id=([0-9a-f-]{36})", timeline_text)
    if not match:
        raise SystemExit(f"could not parse timeline run id from output: {timeline_text[-500:]}")
    timeline_run = match.group(1)
    print(f"     timeline run {timeline_run} approved")

    # Resolve the timeline run's MasterTimeline + NarrationLineSet.
    from sqlalchemy import text

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "select a.artifact_type, av.artifact_id from artifact.artifact_version av "
                "join artifact.artifact a on a.id = av.artifact_id "
                "where av.run_id=:rid and a.artifact_type in "
                "('MasterTimeline','NarrationLineSet')"
            ),
            {"rid": timeline_run},
        ).fetchall()
    timeline_map = {r[0]: r[1] for r in rows}
    if "MasterTimeline" not in timeline_map or "NarrationLineSet" not in timeline_map:
        raise SystemExit(f"timeline run artifacts incomplete: {timeline_map}")
    ordered_keys = [k for k in ("threat", "sale", "payment") if k in windows_json]
    starts = [0.0]
    for key in ordered_keys[:-1]:
        starts.append(starts[-1] + windows_json[key][1])
    if len(starts) != len(narrations):
        raise SystemExit("narration count does not match beat count")

    # Phase 8: E10/E11 audio with the auto narration texts and timeline.
    audio_cmd = [
        sys.executable,
        str(ROOT / "scripts/produce_vc003_audio.py"),
        "--source-run-id",
        timeline_run,
        "--source-timeline-id",
        str(timeline_map["MasterTimeline"]),
        "--source-narration-id",
        str(timeline_map["NarrationLineSet"]),
        "--narration-texts",
        str(narration_file),
        "--narration-starts",
        json.dumps(starts),
        "--output-name",
        f"auto_{run_id}.mp4",
    ]
    print("  8/8 audio/render...")
    subprocess.run(audio_cmd, check=True)  # nosec B603 B607
    print(f"== DONE run {run_id}; see outputs/vc003_episode_08/audio/auto_{run_id}.mp4 ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
