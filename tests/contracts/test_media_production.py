from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import ArtifactRef
from packages.contracts.media_production import (
    MixPlan,
    MixStem,
    SubtitleCue,
    SubtitleCueSet,
    VoiceTake,
    VoiceTakeSet,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def time(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1}


def span(start: int, duration: int) -> dict[str, object]:
    return {"start": time(start), "duration": time(duration)}


def test_selected_voice_take_requires_real_audio_and_take_budget() -> None:
    with pytest.raises(ValidationError, match="committed audio"):
        VoiceTake(
            take_id=uuid4(),
            narration_line_id=uuid4(),
            raw_response_ref=ref("RawProviderResponse"),
            provider_id="tts",
            provider_version="1",
            voice_id="voice",
            disposition="selected",
            estimated_cost_micros=1,
        )
    line_id = uuid4()
    takes = tuple(
        VoiceTake(
            take_id=uuid4(),
            narration_line_id=line_id,
            raw_response_ref=ref("RawProviderResponse"),
            provider_id="tts",
            provider_version="1",
            voice_id="voice",
            disposition="candidate",
            estimated_cost_micros=1,
        )
        for _ in range(2)
    )
    with pytest.raises(ValidationError, match="budget exceeded"):
        VoiceTakeSet(
            narration_line_set_ref=ref("NarrationLineSet"),
            voice_profile_ref=ref("ConfigArtifact"),
            takes=takes,
            max_takes_per_line=1,
        )


def test_mix_requires_narration_and_explicit_bgm_ducking() -> None:
    narration = MixStem(role="narration", source_ref=ref("VoiceAsset"), timeline_range=span(0, 5))
    assert MixPlan(
        conformed_timeline_ref=ref("MasterTimeline"),
        stems=(narration,),
        target_loudness_lufs=-16,
        true_peak_ceiling_dbtp=-1,
        measurement_profile_ref=ref("ConfigArtifact"),
    ).stems
    bgm = MixStem(role="bgm", source_ref=ref("AudioAssetSelection"), timeline_range=span(0, 5))
    with pytest.raises(ValidationError, match="ducking"):
        MixPlan(
            conformed_timeline_ref=ref("MasterTimeline"),
            stems=(narration, bgm),
            target_loudness_lufs=-16,
            true_peak_ceiling_dbtp=-1,
            measurement_profile_ref=ref("ConfigArtifact"),
        )


def test_subtitle_highlight_and_primary_layer_overlap_fail_closed() -> None:
    cue = SubtitleCue(
        cue_id=uuid4(),
        timeline_range=span(0, 2),
        text="真相来了",
        highlighted_ranges=((0, 2),),
        style_ref="primary",
        safe_area={"bottom": 0.2},
    )
    with pytest.raises(ValidationError, match="inside cue text"):
        cue.model_copy(update={"highlighted_ranges": ((0, 99),)}).model_validate(
            cue.model_copy(update={"highlighted_ranges": ((0, 99),)}).model_dump()
        )
    overlap = SubtitleCue.model_validate(
        {**cue.model_dump(mode="json"), "cue_id": uuid4(), "timeline_range": span(1, 2)}
    )
    with pytest.raises(ValidationError, match="cannot overlap"):
        SubtitleCueSet(
            alignment_ref=ref("AlignmentArtifact"),
            cues=(cue, overlap),
            style_profile_ref=ref("ConfigArtifact"),
        )
