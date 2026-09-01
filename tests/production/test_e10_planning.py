"""E10 non-provider planning tests: mix stems and voice-duration conform patch."""

from uuid import uuid4

import pytest

from packages.contracts import ActorRef, ArtifactRef, MasterTimeline, RationalTime, TimeRange
from packages.contracts.media_production import AudioRole
from packages.contracts.timeline import TimelineTrackKind
from packages.production.conform import ConformConflict, duration_delta, plan_voice_conform_patch
from packages.production.mix_planning import MixPlanningConflict, plan_mix_stems


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _us(value: int) -> RationalTime:
    return RationalTime(value=value, rate_num=1_000_000)


def _micro_range(start: int, duration: int) -> TimeRange:
    return TimeRange(start=_us(start), duration=_us(duration))


def _narration_timeline() -> MasterTimeline:
    from packages.contracts.timeline import TimelineItem, TimelineItemType

    items = tuple(
        TimelineItem.model_validate(
            {
                "item_id": str(uuid4()),
                "item_version": 1,
                "item_type": TimelineItemType.TEXT.value,
                "timeline_range": {
                    "start": {"value": start, "rate_num": 1_000_000},
                    "duration": {"value": dur, "rate_num": 1_000_000},
                },
                "content_ref": f"line.{index}",
                "parameters": {"text": f"line {index}"},
            }
        )
        for index, (start, dur) in enumerate([(0, 4_000_000), (4_000_000, 5_000_000)])
    )
    return MasterTimeline.model_validate(
        {
            "timeline_id": str(uuid4()),
            "lifecycle": "draft",
            "rate_num": 1_000_000,
            "global_start": _us(0).model_dump(mode="json"),
            "duration": _us(9_000_000).model_dump(mode="json"),
            "tracks": [
                {
                    "track_id": str(uuid4()),
                    "kind": TimelineTrackKind.NARRATION.value,
                    "order": 2,
                    "items": [item.model_dump(mode="json") for item in items],
                }
            ],
            "metadata_namespace_version": "1.0.0",
        }
    )


def test_duration_delta_requires_same_rate() -> None:
    assert duration_delta(_us(5_000_000), _us(6_000_000)).value == 1_000_000
    with pytest.raises(ConformConflict, match="same rational rate"):
        duration_delta(RationalTime(value=5, rate_num=1), RationalTime(value=6, rate_num=2))


def test_mix_plan_requires_narration_and_covers_original_audio() -> None:
    timeline = _narration_timeline()
    narration_source = _ref("VoiceAsset")
    plan = plan_mix_stems(
        timeline,
        conformed_timeline_ref=_ref("MasterTimeline"),
        narration_source_ref=narration_source,
        target_loudness_lufs=-14.0,
        true_peak_ceiling_dbtp=-1.0,
        measurement_profile_ref=_ref("ConfigArtifact"),
    )
    roles = [stem.role for stem in plan.stems]
    assert AudioRole.NARRATION in roles
    assert plan.target_loudness_lufs == -14.0
    assert len(plan.stems) == 1  # no original-audio tracks in fixture
    narration = next(stem for stem in plan.stems if stem.role is AudioRole.NARRATION)
    assert narration.source_ref == narration_source


def test_mix_plan_requires_narration_track() -> None:

    empty = MasterTimeline.model_validate(
        {
            "timeline_id": str(uuid4()),
            "lifecycle": "draft",
            "rate_num": 1_000_000,
            "global_start": _us(0).model_dump(mode="json"),
            "duration": _us(100).model_dump(mode="json"),
            "tracks": [],
            "metadata_namespace_version": "1.0.0",
        }
    )
    with pytest.raises(MixPlanningConflict, match="no narration track"):
        plan_mix_stems(
            empty,
            conformed_timeline_ref=_ref("MasterTimeline"),
            narration_source_ref=_ref("VoiceAsset"),
            target_loudness_lufs=-14.0,
            true_peak_ceiling_dbtp=-1.0,
            measurement_profile_ref=_ref("ConfigArtifact"),
        )


def test_voice_conform_patch_retimes_item_and_reports_delta() -> None:
    timeline = _narration_timeline()
    item_id = timeline.tracks[0].items[0].item_id
    current_range = timeline.tracks[0].items[0].timeline_range
    author = ActorRef.model_validate({"kind": "human", "id": "e10-conform-test"})
    patch, delta = plan_voice_conform_patch(
        timeline_ref=_ref("MasterTimeline"),
        narration_item_id=item_id,
        current_range=current_range,
        actual_duration=_us(4_500_000),
        author=author,
    )
    assert delta.value == 500_000
    operation = patch.operations[0]
    assert operation.target_item_id == item_id
    payload_range = operation.payload["timeline_range"]
    assert payload_range["duration"]["value"] == 4_500_000
    assert payload_range["start"]["value"] == 0  # start preserved


def test_voice_conform_rejects_zero_delta() -> None:
    with pytest.raises(ConformConflict, match="nothing to conform"):
        plan_voice_conform_patch(
            timeline_ref=_ref("MasterTimeline"),
            narration_item_id=uuid4(),
            current_range=_micro_range(0, 4_000_000),
            actual_duration=_us(4_000_000),
            author=ActorRef.model_validate({"kind": "human", "id": "test"}),
        )
