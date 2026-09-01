import pytest

from packages.longform.transcript_localization import localize_cue, parse_srt


def test_localizes_literal_cue_and_labels_coarse_interpolation() -> None:
    segments = parse_srt(
        "1\n00:00:10,000 --> 00:00:30,000\n前情很多。狼群已经围了上来。随后主角反击。\n"
    )
    cue = localize_cue(segments, "狼群已经围了上来", padding_seconds=2)
    assert 10 <= cue.start_seconds < cue.end_seconds <= 30
    assert cue.precision == "coarse_interpolated"


def test_rejects_unknown_or_empty_cues() -> None:
    segments = parse_srt("1\n00:00:00,000 --> 00:00:02,000\n成交\n")
    with pytest.raises(ValueError, match="cannot be empty"):
        localize_cue(segments, "")
    with pytest.raises(ValueError, match="not found"):
        localize_cue(segments, "五十万")
