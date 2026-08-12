from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef
from packages.contracts.media_production import AlignmentArtifact, AlignmentToken
from packages.production.conform import ConformConflict, build_subtitle_cues, duration_delta


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def time(value: int, rate: int = 1):
    return {"value": value, "rate_num": rate}


def test_actual_voice_duration_delta_requires_exact_rate() -> None:
    from packages.contracts import RationalTime

    assert (
        duration_delta(RationalTime(value=5, rate_num=1), RationalTime(value=7, rate_num=1)).value
        == 2
    )
    with pytest.raises(ConformConflict, match="same rational rate"):
        duration_delta(RationalTime(value=5, rate_num=1), RationalTime(value=7, rate_num=2))


def test_alignment_builds_deterministic_primary_subtitle_cue() -> None:
    line_id = uuid4()
    alignment = AlignmentArtifact(
        voice_asset_ref=ref("VoiceAsset"),
        narration_line_set_ref=ref("NarrationLineSet"),
        tokens=(
            AlignmentToken(
                token="真相",
                line_id=line_id,
                timeline_range={"start": time(0), "duration": time(1)},
            ),
            AlignmentToken(
                token="来了",
                line_id=line_id,
                timeline_range={"start": time(1), "duration": time(1)},
            ),
        ),
        alignment_method="forced-v1",
    )
    cues = build_subtitle_cues(
        alignment=alignment,
        alignment_ref=ref("AlignmentArtifact"),
        style_profile_ref=ref("ConfigArtifact"),
        texts={line_id: "真相来了"},
        cue_ids={line_id: uuid4()},
        safe_area={"bottom": 0.2},
    )
    assert cues.cues[0].timeline_range.duration.seconds == 2
