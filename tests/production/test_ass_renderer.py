"""E10 ASS subtitle renderer tests."""

from uuid import uuid4

from packages.contracts import ArtifactRef
from packages.contracts.media_production import SubtitleCue, SubtitleCueSet
from packages.production.ass_renderer import (
    SubtitleStyle,
    _ass_timestamp,
    render_ass_content,
)


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _us(value: int) -> dict[str, int]:
    return {"value": value, "rate_num": 1_000_000}


def _cue(text: str, start: int, duration: int, *, safe_area=None, highlights=()) -> SubtitleCue:
    return SubtitleCue(
        cue_id=uuid4(),
        timeline_range={"start": _us(start), "duration": _us(duration)},
        text=text,
        highlighted_ranges=highlights,
        style_ref="primary",
        safe_area=safe_area or {"y": 0.8, "height": 0.14},
    )


def test_ass_timestamp_format() -> None:
    from fractions import Fraction

    assert _ass_timestamp(Fraction(0)) == "0:00:00.00"
    assert _ass_timestamp(Fraction(61, 1)) == "0:01:01.00"
    assert _ass_timestamp(Fraction(3725, 1)) == "1:02:05.00"


def test_render_ass_content_produces_dialogue_events() -> None:
    cue_set = SubtitleCueSet(
        alignment_ref=_ref("AlignmentArtifact"),
        cues=(
            _cue("山神印觉醒", 0, 4_000_000),
            _cue("少年初入宗门", 4_000_000, 5_000_000),
        ),
        style_profile_ref=_ref("ConfigArtifact"),
    )
    content = render_ass_content(cue_set)
    assert "ScriptType: v4.00+" in content
    assert "PlayResX: 720" in content
    assert "Dialogue: 0,0:00:00.00,0:00:04.00,Default,,0,0,77,,山神印觉醒" in content
    assert "Dialogue: 0,0:00:04.00,0:00:09.00,Default,,0,0,77,,少年初入宗门" in content


def test_safe_area_margin_v_computes_bottom_margin() -> None:
    cue_set = SubtitleCueSet(
        alignment_ref=_ref("AlignmentArtifact"),
        cues=(_cue("文字", 0, 1_000_000, safe_area={"y": 0.8, "height": 0.14}),),
        style_profile_ref=_ref("ConfigArtifact"),
    )
    content = render_ass_content(cue_set)
    # margin = (1 - 0.8 - 0.14) * 1280 = 76.8 -> 77
    assert ",77,,文字" in content


def test_highlighted_ranges_emit_colour_overrides() -> None:
    cue_set = SubtitleCueSet(
        alignment_ref=_ref("AlignmentArtifact"),
        cues=(_cue("山神印觉醒", 0, 2_000_000, highlights=((0, 2),)),),
        style_profile_ref=_ref("ConfigArtifact"),
    )
    content = render_ass_content(cue_set)
    assert r"{\c&H00FFD479&}山神{\c}印觉醒" in content


def test_custom_style_applied() -> None:
    cue_set = SubtitleCueSet(
        alignment_ref=_ref("AlignmentArtifact"),
        cues=(_cue("文字", 0, 1_000_000),),
        style_profile_ref=_ref("ConfigArtifact"),
    )
    content = render_ass_content(
        cue_set, style=SubtitleStyle(font_name="Source Han Sans", font_size=40, bold=True)
    )
    assert "Source Han Sans,40" in content
    assert ",1,0,0,0," in content  # bold=1


def test_newlines_escaped_to_ass_overrides() -> None:
    cue_set = SubtitleCueSet(
        alignment_ref=_ref("AlignmentArtifact"),
        cues=(_cue("第一行\n第二行", 0, 1_000_000),),
        style_profile_ref=_ref("ConfigArtifact"),
    )
    content = render_ass_content(cue_set)
    assert "第一行\\N第二行" in content


def test_long_cjk_caption_wraps_within_portrait_safe_width() -> None:
    cue_set = SubtitleCueSet(
        alignment_ref=_ref("AlignmentArtifact"),
        cues=(_cue("所有人只看见他的狼狈没人知道群山正在回应他", 0, 2_000_000),),
        style_profile_ref=_ref("ConfigArtifact"),
    )
    content = render_ass_content(cue_set, style=SubtitleStyle(max_chars_per_line=12))
    assert "所有人只看见他的狼狈没人\\N知道群山正在回应他" in content
