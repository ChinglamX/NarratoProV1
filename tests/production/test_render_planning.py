"""E11 render planning tests."""

from uuid import uuid4

from packages.contracts import ArtifactRef, MasterTimeline, TimeRange
from packages.contracts.media_production import AudioRole, MixPlan, MixStem
from packages.contracts.render_release import RenderMode
from packages.contracts.timeline import TimelineItem, TimelineItemType, TimelineTrackKind
from packages.production.render_planning import plan_render_contract


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _us(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1_000_000}


def _timeline() -> MasterTimeline:
    source = _ref("SourceMedia")
    clip = TimelineItem.model_validate(
        {
            "item_id": str(uuid4()),
            "item_version": 1,
            "item_type": TimelineItemType.CLIP.value,
            "timeline_range": {"start": _us(0), "duration": _us(4_000_000)},
            "source_ref": source.model_dump(mode="json"),
            "source_range": {
                "start": {"value": 2_000_000, "rate_num": 1_000_000},
                "duration": {"value": 4_000_000, "rate_num": 1_000_000},
            },
            "parameters": {"target_width": 720, "target_height": 1280},
        }
    )
    return MasterTimeline.model_validate(
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


def _mix_plan() -> MixPlan:
    return MixPlan(
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


def test_plan_render_builds_deterministic_operations() -> None:
    timeline = _timeline()
    mix = _mix_plan()
    timeline_ref = _ref("MasterTimeline")
    mix_ref = _ref("MixPlan")
    ass_ref = _ref("ASSArtifact")
    profile = _ref("ConfigArtifact")

    plan = plan_render_contract(
        timeline=timeline,
        timeline_ref=timeline_ref,
        mix_plan_ref=mix_ref,
        mix_plan=mix,
        ass_ref=ass_ref,
        platform_profile_ref=profile,
    )
    types = [op.operation_type for op in plan.operations]
    assert types == ["trim-clip", "burn-ass", "mix-audio", "mux-final"]
    assert plan.mode is RenderMode.PROXY
    assert plan.expected_duration.seconds == 4.0
    assert plan.checksum.startswith("sha256:")

    plan2 = plan_render_contract(
        timeline=timeline,
        timeline_ref=timeline_ref,
        mix_plan_ref=mix_ref,
        mix_plan=mix,
        ass_ref=ass_ref,
        platform_profile_ref=profile,
    )
    assert plan2.checksum == plan.checksum  # deterministic across identical inputs


def test_plan_render_final_mode_and_different_audio_changes_checksum() -> None:
    timeline = _timeline()
    mix = _mix_plan()
    plan_proxy = plan_render_contract(
        timeline=timeline, timeline_ref=_ref("MasterTimeline"), mix_plan_ref=_ref("MixPlan"),
        mix_plan=mix, ass_ref=_ref("ASSArtifact"), platform_profile_ref=_ref("ConfigArtifact"),
    )
    plan_final = plan_render_contract(
        timeline=timeline, timeline_ref=_ref("MasterTimeline"), mix_plan_ref=_ref("MixPlan"),
        mix_plan=mix, ass_ref=_ref("ASSArtifact"), platform_profile_ref=_ref("ConfigArtifact"),
        mode=RenderMode.FINAL,
    )
    assert plan_final.mode is RenderMode.FINAL
    assert plan_final.checksum != plan_proxy.checksum
    assert any(op.operation_type == "mux-final" and op.parameters["mode"] == "final"
               for op in plan_final.operations)
