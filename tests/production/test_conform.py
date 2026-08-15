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


def _microsecond(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1_000_000}


def test_subtitle_cues_use_microsecond_alignment_time_base() -> None:
    """Regression guard: E09-style rate mixing must not corrupt E10 cue timing.

    Cue ranges are derived from alignment token seconds, so microsecond-based
    alignment must produce the same wall-clock cue times as any other base.
    """
    line_a, line_b = uuid4(), uuid4()
    alignment = AlignmentArtifact(
        voice_asset_ref=ref("VoiceAsset"),
        narration_line_set_ref=ref("NarrationLineSet"),
        tokens=(
            AlignmentToken(
                token="少年",
                line_id=line_a,
                timeline_range={"start": _microsecond(0), "duration": _microsecond(1_000_000)},
            ),
            AlignmentToken(
                token="出山",
                line_id=line_a,
                timeline_range={
                    "start": _microsecond(1_000_000),
                    "duration": _microsecond(1_000_000),
                },
            ),
            AlignmentToken(
                token="宗门",
                line_id=line_b,
                timeline_range={
                    "start": _microsecond(3_500_000),
                    "duration": _microsecond(500_000),
                },
            ),
        ),
        alignment_method="forced-v1",
    )
    cue_ids = {line_a: uuid4(), line_b: uuid4()}
    cues = build_subtitle_cues(
        alignment=alignment,
        alignment_ref=ref("AlignmentArtifact"),
        style_profile_ref=ref("ConfigArtifact"),
        texts={line_a: "少年出山", line_b: "宗门"},
        cue_ids=cue_ids,
        safe_area={"bottom": 0.2},
    )
    by_line = {cue.line_id: cue for cue in cues.cues}
    cue_a = by_line[line_a]
    cue_b = by_line[line_b]
    assert float(cue_a.timeline_range.start.seconds) == pytest.approx(0.0)
    assert float(cue_a.timeline_range.duration.seconds) == pytest.approx(2.0)
    assert float(cue_b.timeline_range.start.seconds) == pytest.approx(3.5)
    assert float(cue_b.timeline_range.duration.seconds) == pytest.approx(0.5)
    assert cue_a.text == "少年出山" and cue_b.text == "宗门"
