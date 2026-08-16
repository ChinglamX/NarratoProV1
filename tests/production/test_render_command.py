"""E11 render command construction tests."""

from pathlib import Path
from uuid import uuid4

import pytest

from packages.contracts import (
    ArtifactRef,
    MasterTimeline,
    RenderPlanContract,
    TimeRange,
)
from packages.contracts.media_production import AudioRole, MixPlan, MixStem
from packages.contracts.render_release import RenderMode
from packages.contracts.timeline import TimelineItem, TimelineItemType, TimelineTrackKind
from packages.production.render_command import (
    RenderCommandError,
    build_render_command,
    libass_available,
)


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _us(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1_000_000}


def _plan() -> RenderPlanContract:
    source = _ref("SourceMedia")
    clip = TimelineItem.model_validate(
        {
            "item_id": str(uuid4()),
            "item_version": 1,
            "item_type": TimelineItemType.CLIP.value,
            "timeline_range": {"start": _us(0), "duration": _us(4_000_000)},
            "source_ref": source.model_dump(mode="json"),
            "source_range": {"start": _us(2_000_000), "duration": _us(4_000_000)},
            "parameters": {},
        }
    )
    timeline = MasterTimeline.model_validate(
        {
            "timeline_id": str(uuid4()),
            "lifecycle": "draft",
            "rate_num": 1_000_000,
            "global_start": _us(0),
            "duration": _us(4_000_000),
            "tracks": [
                {
                    "track_id": str(uuid4()),
                    "kind": TimelineTrackKind.VIDEO.value,
                    "order": 0,
                    "items": [clip.model_dump(mode="json")],
                }
            ],
            "metadata_namespace_version": "1.0.0",
        }
    )
    mix = MixPlan(
        conformed_timeline_ref=_ref("MasterTimeline"),
        stems=(
            MixStem(
                role=AudioRole.NARRATION,
                source_ref=_ref("VoiceAsset"),
                timeline_range=TimeRange.model_validate(
                    {"start": _us(0), "duration": _us(4_000_000)}
                ),
            ),
        ),
        target_loudness_lufs=-14.0,
        true_peak_ceiling_dbtp=-1.0,
        measurement_profile_ref=_ref("ConfigArtifact"),
    )
    from packages.production.render_planning import plan_render_contract

    return plan_render_contract(
        timeline=timeline,
        timeline_ref=_ref("MasterTimeline"),
        mix_plan_ref=_ref("MixPlan"),
        mix_plan=mix,
        ass_ref=_ref("ASSArtifact"),
        platform_profile_ref=_ref("ConfigArtifact"),
        mode=RenderMode.PROXY,
    )


def test_build_render_command_structure(tmp_path: Path) -> None:
    plan = _plan()
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake")
    ass = tmp_path / "out.ass"
    ass.write_text("[Script Info]\n")
    command = build_render_command(
        plan=plan,
        source_paths={str(plan.operations[0].input_refs[0].artifact_id): source},
        ass_path=ass,
        output_path=tmp_path / "out.mp4",
    )
    assert command[0] == "ffmpeg"
    assert "-filter_complex" in command
    assert "concat=n=1:v=1:a=0" in "".join(command)
    assert "subtitles=" in "".join(command)
    assert "-c:v" in command and "libx264" in command
    assert str(tmp_path / "out.mp4") in command


def test_build_render_command_missing_source_raises(tmp_path: Path) -> None:
    plan = _plan()
    with pytest.raises(RenderCommandError, match="source media unavailable"):
        build_render_command(
            plan=plan, source_paths={}, ass_path=tmp_path / "x.ass", output_path=tmp_path / "o.mp4"
        )


def test_libass_detection_returns_bool() -> None:
    assert isinstance(libass_available(), bool)
