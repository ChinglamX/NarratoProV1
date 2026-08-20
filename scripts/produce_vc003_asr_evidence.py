"""Episode 8 real ASR evidence windows + VLM refinement loop (research).

1. Runs FunASR (paraformer-large, diarization) on the Episode 8 AudioStem and
   parses the timed SRT into segments (the SRT is cached in tmp/ep8_asr.srt).
2. Maps the three approved Story events to ASR segments by dialogue keywords,
   producing *evidence windows*.
3. Refines each evidence window with the cached VLM relevance verdicts
   (evidence-first + VLM re-rank), producing auto clip candidate windows.
4. Commits the raw ASR response as a RawProviderResponse artifact and writes
   an evidence card comparing ASR / refined / human-verified windows.

Everything is research: no approved artifact changes; confidence unavailable;
L1 human review applies.
"""

# ruff: noqa: RUF001 - CJK dialogue and review copy are intentional.

from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import UUID, uuid4

from packages.contracts import ActorRef, ArtifactRef
from packages.foundation.settings import get_settings
from packages.intelligence.vlm_clip_retrieval import (
    FrameRelevance,
    parse_relevance_verdict,
    refine_evidence_window,
)
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
RUN_ID = UUID("d3690d71-444a-43d9-bbd0-52bd1c91d371")
STORY_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "c378ba51-da33-4049-baf0-538ca637e9a5",
        "version": 1,
        "artifact_type": "StoryGraph",
        "checksum": "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
    }
)
SRT_PATH = ROOT / "tmp" / "ep8_asr.srt"
VERDICT_CACHE = ROOT / "tmp" / "vc003_vlm_verdicts.json"
OUT_DIR = ROOT / "outputs/vc003_episode_08/asr_evidence"
TRACE_ID = "8e008000000000000000000000000008"
ACTOR = ActorRef.model_validate({"kind": "model", "id": "vc003-research-funasr-evidence"})

# Event -> (story event id, evidence id, dialogue keywords to match in ASR text,
# human-verified claim window for comparison).
EVENTS = (
    (
        UUID("87f8ff89-54ec-42b1-8e46-c12cefba6e47"),
        UUID("1267ab6e-3cc8-4a10-8ef5-5764077f0616"),
        "threat",
        ("那小子",),
        (42.0, 50.0),
    ),
    (
        UUID("1df88e31-efac-44ac-8e73-8bcb5c8269ec"),
        UUID("172bf99b-af5d-4070-b836-ec6d50eedf58"),
        "sale",
        ("我都要了", "成交"),
        (15.0, 28.0),
    ),
    (
        UUID("1c583c8c-7291-4f8f-91e9-b02181958c26"),
        UUID("d008fa4a-3bd6-40c0-83f3-79885d89b34d"),
        "payment",
        ("密码", "卡里有"),
        (28.0, 33.0),
    ),
)

SRT_PATTERN = re.compile(
    r"\d+\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*\n(.+?)(?=\n\n|\Z)",
    re.DOTALL,
)


def _seconds(timestamp: str) -> float:
    hours, minutes, tail = timestamp.split(":")
    whole, millis = tail.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis) / 1000


def parse_srt(content: str) -> list[dict[str, object]]:
    segments = []
    for start, end, text in SRT_PATTERN.findall(content.strip()):
        speaker = None
        matched = re.match(
            r"说话人([^:\N{FULLWIDTH COLON}]+)[:\N{FULLWIDTH COLON}]\s*(.*)",
            text.strip(),
            re.DOTALL,
        )
        if matched:
            speaker, text = matched.group(1).strip(), matched.group(2).strip()
        segments.append(
            {
                "start_seconds": _seconds(start),
                "end_seconds": _seconds(end),
                "text": text.strip(),
                "speaker": speaker,
            }
        )
    return segments


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = min(a[1], b[1]) - max(a[0], b[0])
    if inter <= 0:
        return 0.0
    union = max(a[1], b[1]) - min(a[0], b[0])
    return round(inter / union, 3) if union > 0 else 0.0


def main() -> int:
    if not SRT_PATH.is_file():
        raise SystemExit(f"ASR SRT missing: run the FunASR service and produce {SRT_PATH}")
    segments = parse_srt(SRT_PATH.read_text(encoding="utf-8"))
    verdicts_raw = json.loads(VERDICT_CACHE.read_text(encoding="utf-8"))
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    card_rows: list[dict[str, object]] = []
    raw_payload = {
        "provider": "funasr-local-research",
        "model": "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        "diarization": True,
        "segments": segments,
    }
    engine = create_database_engine(get_settings().database_url)
    with engine.begin() as connection:
        repository = ArtifactRepository()
        raw_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="RawProviderResponse",
            payload=raw_payload,
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=ACTOR,
            producer_module="vc003-research-funasr-evidence",
            module_version="0.1.0",
            resource_profile_ref=STORY_REF,
            rights_class="internal-preview",
            inputs=(STORY_REF,),
        )
    engine.dispose()

    for event_id, evidence_id, key, keywords, human_window in EVENTS:
        matched = [s for s in segments if any(k in s["text"] for k in keywords)]
        if not matched:
            print(f"event {key}: no ASR segments matched")
            continue
        asr_window = (matched[0]["start_seconds"], matched[-1]["end_seconds"])
        frames = [
            FrameRelevance(
                frame_seconds=float(t),
                relevant=parse_relevance_verdict(verdict),
                raw_verdict=verdict,
            )
            for t, verdict in verdicts_raw.get(str(event_id), {}).items()
        ]
        refined = refine_evidence_window(frames, asr_window)
        card_rows.append(
            {
                "event": key,
                "story_event_id": str(event_id),
                "evidence_id": str(evidence_id),
                "asr_window_seconds": [round(asr_window[0], 3), round(asr_window[1], 3)],
                "asr_segments": [
                    {
                        "t": [round(s["start_seconds"], 2), round(s["end_seconds"], 2)],
                        "text": s["text"],
                    }
                    for s in matched
                ],
                "refined_vlm_window_seconds": [round(refined[0], 3), round(refined[1], 3)],
                "human_window_seconds": list(human_window),
                "asr_vs_human_overlap": _overlap(asr_window, human_window),
                "refined_vs_human_overlap": _overlap(refined, human_window),
            }
        )
        print(
            f"{key:<8} ASR {asr_window[0]:6.2f}-{asr_window[1]:6.2f}s "
            f"(overlap {_overlap(asr_window, human_window)}) -> refined "
            f"{refined[0]:6.2f}-{refined[1]:6.2f}s "
            f"(overlap {_overlap(refined, human_window)})  human={list(human_window)}"
        )

    manifest = {
        "scope": "Episode 8 real ASR evidence + VLM refinement loop; research; "
        "confidence unavailable; L1 review required",
        "raw_provider_response_ref": raw_ref.model_dump(mode="json", exclude_none=True),
        "events": card_rows,
        "boundary_notes": [
            "FunASR paraformer-large (research) with diarization; not production admitted.",
            "ASR windows are evidence for auto clip selection; VLM re-ranks within them.",
            "No approved artifact changed; human timeline checkpoint still applies.",
        ],
    }
    (out_dir / "asr_evidence_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = ["# Episode 8 — 真实 ASR 证据窗口 + VLM 精修（research）", ""]
    for row in card_rows:
        md.append(
            f"- **{row['event']}**：ASR {row['asr_window_seconds'][0]}–"
            f"{row['asr_window_seconds'][1]}s (overlap {row['asr_vs_human_overlap']}) → "
            f"VLM 精修 {row['refined_vlm_window_seconds'][0]}–"
            f"{row['refined_vlm_window_seconds'][1]}s (overlap {row['refined_vs_human_overlap']})；"
            f"人工 {row['human_window_seconds'][0]}–{row['human_window_seconds'][1]}s"
        )
    md.append("")
    md.extend(f"- {note}" for note in manifest["boundary_notes"])
    (out_dir / "asr_evidence_card.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"== card: {out_dir}/asr_evidence_card.md ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
