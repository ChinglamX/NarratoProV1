#!/usr/bin/env python3
"""Build the existing canonical MasterTimeline and render a low-cost long-form preview."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

from packages.contracts import ArtifactRef, RationalTime
from packages.contracts.timeline import TimelineTrackKind
from packages.contracts.timeline_intent import NarrationLineSet
from packages.longform.canonical_adapter import project_to_canonical_timeline_inputs
from packages.longform.clip_planning import ChapterClipPlan, ClipPlanningFinding, SelectedShot
from packages.longform.planning import Chapter, ChapterBlueprint, ChapterFunction
from packages.production.real_preview import render_media_preview
from packages.timeline.intent_projection import project_original_audio_intents
from packages.timeline.multitrack import assemble_multitrack_timeline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blueprints", type=Path, required=True)
    parser.add_argument("--selected-shots", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    blueprint = _blueprint(json.loads(args.blueprints.read_text(encoding="utf-8"))[0])
    clip_plan = _clip_plan(json.loads(args.selected_shots.read_text(encoding="utf-8")))
    if clip_plan.blocked:
        raise ValueError("selected shot plan remains blocked")

    source_paths = sorted({shot.source_path for shot in clip_plan.selected})
    source_refs = {path: _ref("SourceMedia", f"source:{path}") for path in source_paths}
    event_ids = sorted({ref for chapter in blueprint.chapters for ref in chapter.event_refs})
    story_refs = {event_id: _uuid(f"story:{event_id}") for event_id in event_ids}
    evidence_refs = {
        shot.shot_id: (_uuid(f"evidence:{shot.shot_id}"),) for shot in clip_plan.selected
    }
    creative_ref = _ref("CreativeBrief", f"creative:{blueprint.arc_id}")
    candidate_set_ref = _ref("ClipCandidateSet", f"candidates:{blueprint.arc_id}")
    canonical = project_to_canonical_timeline_inputs(
        blueprint=blueprint,
        clip_plan=clip_plan,
        creative_brief_ref=creative_ref,
        candidate_set_ref=candidate_set_ref,
        source_refs=source_refs,
        story_refs=story_refs,
        evidence_refs=evidence_refs,
    )
    audio = project_original_audio_intents(
        canonical.selection_plan, canonical.candidate_set.candidates
    )
    narration = NarrationLineSet(
        creative_brief_ref=creative_ref,
        rhythm_plan_ref=_ref("RhythmPlan", f"rhythm:{blueprint.arc_id}"),
        lines=(),
        estimated_duration=_time(0),
    )
    track_ids = {
        TimelineTrackKind.VIDEO: _uuid(f"track:video:{blueprint.arc_id}"),
        TimelineTrackKind.ORIGINAL_AUDIO: _uuid(f"track:original:{blueprint.arc_id}"),
    }
    item_count = len(canonical.selection_plan.selections) + len(audio)
    timeline, report = assemble_multitrack_timeline(
        timeline_id=_uuid(f"timeline:{blueprint.arc_id}"),
        selections=canonical.selection_plan,
        candidates=canonical.candidate_set.candidates,
        narration=narration,
        audio_intents=audio,
        subtitle_intents=(),
        overlay_intents=(),
        dependencies=(creative_ref, candidate_set_ref),
        track_ids=track_ids,
        item_ids=tuple(_uuid(f"item:{blueprint.arc_id}:{index}") for index in range(item_count)),
        duration=_time(blueprint.target_seconds),
    )
    if timeline is None:
        raise ValueError(f"canonical assembly blocked: {report.model_dump(mode='json')}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "master_timeline.json").write_text(
        timeline.model_dump_json(indent=2), encoding="utf-8"
    )
    (args.output_dir / "assembly_report.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    path_by_ref = {reference.artifact_id: Path(path) for path, reference in source_refs.items()}
    preview = render_media_preview(
        timeline,
        path_by_ref,
        args.output_dir / "preview_original_audio.mp4",
    )
    (args.output_dir / "preview_result.json").write_text(
        json.dumps(
            {
                "output_path": str(preview.output_path),
                "duration_seconds": float(preview.duration_seconds),
                "video_codec": preview.video_codec,
                "audio_codec": preview.audio_codec,
                "width": preview.width,
                "height": preview.height,
                "ffmpeg_version": preview.ffmpeg_version,
                "purpose": "low-cost story/continuity review before narration TTS",
                "release_boundary": "internal-preview-only",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"canonical preview: {preview.duration_seconds}s / {preview.width}x{preview.height}")
    print(f"output: {preview.output_path.resolve()}")
    return 0


def _blueprint(raw: dict[str, Any]) -> ChapterBlueprint:
    chapters = raw["chapters"]
    assert isinstance(chapters, list)  # nosec B101 - validated planning artifact
    return ChapterBlueprint(
        arc_id=str(raw["arc_id"]),
        target_seconds=float(raw["target_seconds"]),
        chapters=tuple(
            Chapter(
                chapter_id=str(item["chapter_id"]),
                function=ChapterFunction(str(item["function"])),
                event_refs=tuple(str(value) for value in item["event_refs"]),
                target_seconds=float(item["target_seconds"]),
                narration_budget_seconds=float(item["narration_budget_seconds"]),
                protects_original_audio=bool(item["protects_original_audio"]),
            )
            for item in chapters
        ),
        findings=tuple(str(item) for item in raw.get("findings", [])),
    )


def _clip_plan(raw: dict[str, Any]) -> ChapterClipPlan:
    selected = raw["selected"]
    findings = raw["findings"]
    assert isinstance(selected, list) and isinstance(findings, list)  # nosec B101
    return ChapterClipPlan(
        target_seconds=float(raw["target_seconds"]),
        selected=tuple(SelectedShot(**item) for item in selected),
        findings=tuple(ClipPlanningFinding(**item) for item in findings),
    )


def _ref(kind: str, key: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": _uuid(key), "version": 1, "artifact_type": kind}
    )


def _uuid(key: str) -> UUID:
    raw = bytearray(sha256(key.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))


def _time(seconds: float) -> RationalTime:
    return RationalTime(value=round(seconds * 1_000_000), rate_num=1_000_000)


if __name__ == "__main__":
    raise SystemExit(main())
