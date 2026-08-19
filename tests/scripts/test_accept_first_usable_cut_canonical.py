from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from packages.contracts import ArtifactRef, RationalTime
from packages.contracts.timeline import TimelineTrackKind
from packages.contracts.timeline_intent import (
    DialogueRelationship,
    NarrationLine,
    NarrationLineSet,
)
from scripts.accept_first_usable_cut_canonical import (
    _manual_source_timeline,
    _personal_config_profile,
)


def _ref() -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": 1, "artifact_type": "SourceMedia"}
    )


def _narration(source_ref: ArtifactRef) -> NarrationLineSet:
    line = NarrationLine(
        line_id=uuid4(),
        beat_id=uuid4(),
        text="测试解说",
        function="hook",
        story_refs=(uuid4(),),
        evidence_refs=(uuid4(),),
        target_duration=RationalTime(value=1, rate_num=1),
        dialogue_relationship=DialogueRelationship.COMPLEMENT,
        locked=True,
    )
    return NarrationLineSet(
        creative_brief_ref=source_ref,
        rhythm_plan_ref=source_ref,
        lines=(line,),
        estimated_duration=RationalTime(value=1, rate_num=1),
    )


def test_personal_profile_resolves_all_ingested_sources(tmp_path: Path) -> None:
    source_a = tmp_path / "7.mp4"
    source_b = tmp_path / "8.mp4"
    ref_a, ref_b = _ref(), _ref()
    for index, (source, reference) in enumerate(((source_a, ref_a), (source_b, ref_b)), 1):
        (tmp_path / f"ingest_{index}.json").write_text(
            json.dumps(
                {
                    "run_id": str(uuid4()),
                    "source_path": str(source),
                    "artifacts": {"source": reference.model_dump(mode="json")},
                }
            ),
            encoding="utf-8",
        )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "output": str(tmp_path / "candidate.mp4"),
                "segments": [
                    {"source_path": str(source_a), "duration_seconds": 2},
                    {"source_path": str(source_b), "duration_seconds": 3},
                ],
            }
        ),
        encoding="utf-8",
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "ingest_manifests": ["ingest_1.json", "ingest_2.json"],
                "candidate_manifest": "manifest.json",
            }
        ),
        encoding="utf-8",
    )

    profile = _personal_config_profile(config)

    assert profile.total_duration == 5
    assert dict(profile.source_media_by_path) == {
        str(source_a.resolve()): ref_a,
        str(source_b.resolve()): ref_b,
    }


def test_manual_timeline_keeps_per_segment_source_refs() -> None:
    ref_a, ref_b = _ref(), _ref()
    manifest = {
        "segments": [
            {"source_path": "/source/7.mp4", "source_start_seconds": 2, "duration_seconds": 2},
            {"source_path": "/source/8.mp4", "source_start_seconds": 4, "duration_seconds": 2},
        ],
        "narration_lines": [
            {
                "timeline_start_seconds": 0.2,
                "anchor_source": "tool",
                "required_event_ids": ["event-a"],
            }
        ],
    }
    narration = _narration(ref_a)

    timeline = _manual_source_timeline(
        manifest,
        {"/source/7.mp4": ref_a, "/source/8.mp4": ref_b},
        narration,
    )

    video = next(track for track in timeline.tracks if track.kind is TimelineTrackKind.VIDEO)
    assert tuple(item.source_ref for item in video.items) == (ref_a, ref_b)
    assert timeline.dependencies == (ref_a, ref_b)
    narration_track = next(
        track for track in timeline.tracks if track.kind is TimelineTrackKind.NARRATION
    )
    assert narration_track.items[0].parameters["anchor_source"] == "tool"
    assert narration_track.items[0].parameters["required_event_ids"] == ["event-a"]
