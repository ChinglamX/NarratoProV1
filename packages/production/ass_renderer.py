"""Deterministic E10 ASS subtitle renderer from a SubtitleCueSet."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from packages.contracts.media_production import SubtitleCueSet


class SubtitleStyle:
    """Versioned ASS style derived from a libass/typography profile."""

    def __init__(
        self,
        *,
        font_name: str = "PingFang SC",
        font_size: int = 48,
        primary_colour: str = "&H00FFFFFF",
        outline_colour: str = "&H00000000",
        bold: bool = False,
        outline: int = 3,
        shadow: int = 1,
        play_res_x: int = 720,
        play_res_y: int = 1280,
    ) -> None:
        self.font_name = font_name
        self.font_size = font_size
        self.primary_colour = primary_colour
        self.outline_colour = outline_colour
        self.bold = bold
        self.outline = outline
        self.shadow = shadow
        self.play_res_x = play_res_x
        self.play_res_y = play_res_y


def _ass_timestamp(seconds: Fraction) -> str:
    centiseconds = round(float(seconds) * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def _safe_area_margin_v(safe_area: dict[str, Any], style: SubtitleStyle) -> int:
    """Bottom margin in pixels so text sits inside the declared safe area.

    safe_area is a JSON object with keys y/height (fractions of frame height).
    MarginV = (1 - y - height) * frame_height, plus a small padding.
    """
    y = float(safe_area.get("y", 0.8))
    height = float(safe_area.get("height", 0.14))
    return max(0, round((1.0 - y - height) * style.play_res_y))


def _escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\N")


def _render_cue_text(text: str, highlighted: tuple[tuple[int, int], ...]) -> str:
    text = text.strip()
    if not text:
        return ""
    if highlighted:
        parts: list[str] = []
        cursor = 0
        for start, end in highlighted:
            parts.append(_escape_text(text[cursor:start]))
            parts.append(r"{\c&H00FFD479&}" + _escape_text(text[start:end]) + r"{\c}")
            cursor = end
        parts.append(_escape_text(text[cursor:]))
        return "".join(parts)
    return _escape_text(text)


def render_ass_content(
    cue_set: SubtitleCueSet,
    *,
    style: SubtitleStyle | None = None,
) -> str:
    """Render a SubtitleCueSet into ASS dialogue content.

    Returns the full ASS document text (Script Info + Styles + Events).
    """
    style = style or SubtitleStyle()
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {style.play_res_x}",
        f"PlayResY: {style.play_res_y}",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,"
        "BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,"
        "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        (
            f"Style: Default,{style.font_name},{style.font_size},{style.primary_colour},"
            f"&H000000FF,{style.outline_colour},&H80000000,{int(style.bold)},0,0,0,"
            f"100,100,0,0,1,{style.outline},{style.shadow},2,40,40,120,1"
        ),
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    for cue in cue_set.cues:
        start = _ass_timestamp(cue.timeline_range.start.seconds)
        end = _ass_timestamp(cue.timeline_range.end_seconds)
        margin_v = _safe_area_margin_v(cue.safe_area, style)
        text = _render_cue_text(cue.text, cue.highlighted_ranges)
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,{margin_v},,{text}")
    return "\n".join(lines) + "\n"
