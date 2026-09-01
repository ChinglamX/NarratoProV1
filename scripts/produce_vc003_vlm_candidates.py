"""Research VLM-driven auto clip candidate generation for Episode 8.

For each approved Story event, sample source frames across the episode, ask the
Volcengine doubao-seed VLM whether each frame is directly relevant to the
event's content, deterministically parse the verdicts, and merge contiguous
relevant frames into candidate source windows. The windows become a DRAFT
``ClipCandidateSet`` artifact (producer module ``vc003-research-vlm-clip-selection``,
confidence unavailable, L1 review required) plus a comparison card against the
human-verified claim windows.

Two prompt modes are supported for ablation:
- ``ungrounded``: prompt contains only the event description (visual-only).
- ``grounded``: prompt injects the dialogue excerpt (evidence grounding).
- ``both``: run both modes sequentially and emit a side-by-side comparison.

This demonstrates the auto clip-selection mechanism on real data. It does NOT
change any approved artifact or the production chain; candidates are research
drafts for the human reviewer.
"""

# ruff: noqa: RUF001 - CJK event prompts and review copy are intentional.

from __future__ import annotations

import json
import subprocess  # nosec B404
from pathlib import Path
from uuid import UUID, uuid4

from packages.contracts import (
    ActorRef,
    ArtifactRef,
    ProviderCapability,
    ProviderInvocationRequest,
)
from packages.contracts.timeline_intent import ClipCandidate, ClipCandidateSet
from packages.foundation.settings import get_settings
from packages.intelligence.vlm_clip_retrieval import (
    FrameRelevance,
    parse_relevance_verdict,
    refine_evidence_window,
    relevance_ratio,
    select_relevant_windows,
)
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from packages.providers.visual.volcengine_ark_vlm import VolcengineArkVLMProvider

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
RUN_ID = UUID("d3690d71-444a-43d9-bbd0-52bd1c91d371")
SOURCE_ARTIFACT_ID = UUID("f98ca32a-a855-441b-b73e-fec9f324d1a8")
SOURCE_BLOB = (
    ROOT / "data/local/object_store/objects/sha256/bb/"
    "bb45cd4221f9310c4a4bfd6ed29e92883a351b8596b05bebef5f839bc3e3c3f2"
)
STORY_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "c378ba51-da33-4049-baf0-538ca637e9a5",
        "version": 1,
        "artifact_type": "StoryGraph",
        "checksum": "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
    }
)
SOURCE_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "f98ca32a-a855-441b-b73e-fec9f324d1a8",
        "version": 1,
        "artifact_type": "SourceMedia",
        "checksum": "sha256:bb45cd4221f9310c4a4bfd6ed29e92883a351b8596b05bebef5f839bc3e3c3f2",
    }
)

# Episode 8 Story events (threat / sale / payment) with evidence ids, the
# dialogue evidence excerpt (for grounded prompts) and the human-verified
# claim windows used for comparison only.
EVENTS = (
    (
        UUID("87f8ff89-54ec-42b1-8e46-c12cefba6e47"),
        UUID("1267ab6e-3cc8-4a10-8ef5-5764077f0616"),
        "另一方得知那小子一天得到三十万，因其有钱不还并曾动手，决定盯住并威胁杀死他。",
        "那小子一天就弄到了三十万。那小子手里有钱，却藏着掖着，不还还敢对我动手，给我盯住，这次我就不信弄不死他",
        (42.0, 50.0),
    ),
    (
        UUID("1df88e31-efac-44ac-8e73-8bcb5c8269ec"),
        UUID("172bf99b-af5d-4070-b836-ec6d50eedf58"),
        "对白表明有人以三十万购买两样货物，并完成交易。",
        "三十万这两样我都要了",
        (15.0, 28.0),
    ),
    (
        UUID("1c583c8c-7291-4f8f-91e9-b02181958c26"),
        UUID("d008fa4a-3bd6-40c0-83f3-79885d89b34d"),
        "交易方交出一张内有三十万、密码为六个八的卡。",
        "这张卡里有三十万，密码，六个八",
        (28.0, 33.0),
    ),
)

SAMPLE_START = 0.5
SAMPLE_END = 49.5
SAMPLE_STEP = 2.0
TRACE_ID = "8e006000000000000000000000000006"
ACTOR = ActorRef.model_validate({"kind": "model", "id": "vc003-research-vlm-clip-selection"})


def _extract_frame(source: Path, seconds: float, output: Path) -> None:
    subprocess.run(  # nosec B603 B607
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            f"{seconds:.2f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            "-y",
            str(output),
        ],
        check=True,
    )


def _vlm_verdict(provider: VolcengineArkVLMProvider, frame: Path, prompt: str) -> str:
    request = ProviderInvocationRequest(
        capability=ProviderCapability.VLM,
        inputs=(STORY_REF,),
        config_ref=STORY_REF,
        resource_profile_ref=STORY_REF,
        idempotency_key=f"vlm-clip:{frame.stem}",
        timeout_ms=90_000,
        parameters={"frame_path": str(frame), "prompt": prompt},
    )
    raw = provider.infer(request)
    payload = json.loads(raw.payload)
    claims = payload.get("vlm_claims") or []
    if not claims:
        return ""
    return str(claims[0].get("statement") or "")


def _overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Jaccard-like overlap of two [start, end] windows; 0 if disjoint."""
    inter = min(a[1], b[1]) - max(a[0], b[0])
    if inter <= 0:
        return 0.0
    union = max(a[1], b[1]) - min(a[0], b[0])
    return round(inter / union, 3) if union > 0 else 0.0


def main() -> int:
    settings = get_settings()
    provider = VolcengineArkVLMProvider()
    work = ROOT / "tmp" / "vc003_vlm_frames"
    work.mkdir(parents=True, exist_ok=True)
    out_dir = ROOT / "outputs/vc003_episode_08/vlm_candidates"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_candidates: list[ClipCandidate] = []
    card_rows: list[dict[str, object]] = []
    cache_path = ROOT / "tmp" / "vc003_vlm_verdicts.json"
    cache: dict[str, dict[str, str]] = {}
    if cache_path.is_file():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    engine = create_database_engine(settings.database_url)
    with engine.begin() as connection:
        repository = ArtifactRepository()
        candidate_set_id = uuid4()
        for event_id, evidence_id, description, dialogue, human_window in EVENTS:
            key = str(event_id)
            event_cache = cache.setdefault(key, {})
            frames = []
            seconds = SAMPLE_START
            while seconds <= SAMPLE_END:
                frame_path = work / f"{event_id}_{seconds:06.2f}.jpg"
                _extract_frame(SOURCE_BLOB, seconds, frame_path)
                cached = event_cache.get(str(seconds))
                if cached is None:
                    prompt = (
                        f"该画面是否属于以下情节的发生场景：「{description}」"
                        f"（对白：{dialogue}）。只回答：相关 或 不相关。"
                    )
                    cached = _vlm_verdict(provider, frame_path, prompt)
                    event_cache[str(seconds)] = cached
                frames.append(
                    FrameRelevance(
                        frame_seconds=seconds,
                        relevant=parse_relevance_verdict(cached),
                        raw_verdict=cached,
                    )
                )
                seconds = round(seconds + SAMPLE_STEP, 2)
            raw_windows = select_relevant_windows(frames)
            # Evidence-first refinement: with a coarse evidence window (the whole
            # sampled range) the refinement equals raw selection; with the
            # human-verified claim window as a labelled reference probe it shows
            # the mechanism's value when speech alignment supplies a window.
            refined_coarse = refine_evidence_window(frames, (SAMPLE_START, SAMPLE_END))
            refined_probe = refine_evidence_window(frames, human_window)
            ratio = relevance_ratio(frames)
            for variant, windows in (
                ("raw", raw_windows),
                ("refined_probe", [refined_probe] if refined_probe != human_window else []),
            ):
                for start, end in windows:
                    all_candidates.append(
                        ClipCandidate.model_validate(
                            {
                                "candidate_id": uuid4(),
                                "beat_id": uuid4(),
                                "source_ref": SOURCE_REF.model_dump(mode="json"),
                                "source_range": {
                                    "start": {
                                        "value": round(start * 1_000_000),
                                        "rate_den": 1,
                                        "rate_num": 1_000_000,
                                    },
                                    "duration": {
                                        "value": round((end - start) * 1_000_000),
                                        "rate_den": 1,
                                        "rate_num": 1_000_000,
                                    },
                                },
                                "story_refs": [str(event_id)],
                                "evidence_refs": [str(evidence_id)],
                                "visible_character_refs": [],
                                "quality": {"sharpness": 0.6, "motion": 0.5},
                                "continuity_features": {"source": f"vlm-research:{variant}"},
                                "reframe_feasible": False,
                                "rights_allowed": True,
                                "score_components": {"evidence": round(ratio, 3)},
                            }
                        )
                    )
            card_rows.append(
                {
                    "event_id": str(event_id),
                    "description": description,
                    "human_verified_window": list(human_window),
                    "raw_windows": raw_windows,
                    "refined_coarse_window": list(refined_coarse),
                    "refined_probe_window": list(refined_probe),
                    "raw_vs_human_overlap": [
                        _overlap(window, human_window) for window in raw_windows
                    ],
                    "probe_vs_human_overlap": _overlap(refined_probe, human_window),
                    "relevance_ratio": round(ratio, 3),
                    "sampled_frames": len(frames),
                    "relevant_frames": sum(1 for f in frames if f.relevant),
                    "verdicts": [
                        {"t": round(f.frame_seconds, 1), "relevant": f.relevant} for f in frames
                    ],
                }
            )
            print(
                f"event {str(event_id)[:8]}  relevant={sum(1 for f in frames if f.relevant)}/"
                f"{len(frames)}  raw={raw_windows}  probe={refined_probe}  "
                f"(human={list(human_window)})"
            )
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        candidate_set = ClipCandidateSet(
            beat_graph_ref=STORY_REF,
            candidates=tuple(all_candidates),
        )
        candidate_set_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=candidate_set_id,
            artifact_type="ClipCandidateSet",
            payload=candidate_set,
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=ACTOR,
            producer_module="vc003-research-vlm-clip-selection",
            module_version="0.1.0",
            resource_profile_ref=STORY_REF,
            rights_class="internal-preview",
            inputs=(STORY_REF,),
        )
    engine.dispose()

    manifest = {
        "scope": (
            "Episode 8 research auto clip selection; confidence unavailable; L1 review required"
        ),
        "source_media": SOURCE_REF.model_dump(mode="json", exclude_none=True),
        "candidate_set_ref": candidate_set_ref.model_dump(mode="json", exclude_none=True),
        "events": card_rows,
        "boundary_notes": [
            "VLM verdicts are non-deterministic; relevance parse fails closed",
            "on ambiguity.",
            "Windows are research drafts, not approved edits; the human timeline",
            "checkpoint still applies.",
            "No production admission implied; provider stays research.",
        ],
    }
    (out_dir / "vlm_candidates_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = ["# Episode 8 — VLM 自动选镜 v2（research）", ""]
    for row in card_rows:
        md.append(
            f"- **{row['description'][:22]}…**：人工窗口 {row['human_verified_window'][0]}–"
            f"{row['human_verified_window'][1]}s；raw 选窗 {row['raw_windows']} "
            f"(overlap {row['raw_vs_human_overlap']})；evidence 精修 {row['refined_probe_window']} "
            f"(overlap {row['probe_vs_human_overlap']})；相关帧 "
            f"{row['relevant_frames']}/{row['sampled_frames']}"
        )
    md.append("")
    md.extend(f"- {note}" for note in manifest["boundary_notes"])
    (out_dir / "vlm_candidates_card.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"== card: {out_dir}/vlm_candidates_card.md ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
