"""Deterministic FFmpeg fake preview renderer for foundation acceptance."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

from packages.contracts import MasterTimeline
from packages.timeline.validator import validate_timeline


class PreviewRenderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PreviewResult:
    output_path: Path
    subtitle_path: Path
    duration_seconds: Fraction
    video_codec: str
    audio_codec: str
    width: int
    height: int
    ffmpeg_version: str


def _ass_timestamp(seconds: Fraction) -> str:
    centiseconds = round(float(seconds) * 100)
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def _write_ass(path: Path, duration: Fraction) -> None:
    content = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,"
        "BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,"
        "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,"
        "100,100,0,0,1,3,1,2,40,40,100,1\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        f"Dialogue: 0,0:00:00.00,{_ass_timestamp(duration)},Default,,0,0,0,,"
        "NarratoPro Foundation Preview\n"
    )
    path.write_text(content, encoding="utf-8")


def _probe(ffprobe: str, output_path: Path) -> dict[str, Any]:
    completed = subprocess.run(  # nosec B603
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height:format=duration",
            "-of",
            "json",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return cast(dict[str, Any], json.loads(completed.stdout))


def render_fake_preview(timeline: MasterTimeline, output_path: Path) -> PreviewResult:
    if not validate_timeline(timeline).render_ready:
        raise PreviewRenderError("timeline is not render-ready")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise PreviewRenderError("ffmpeg and ffprobe are required")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = timeline.duration.seconds
    duration_text = f"{float(duration):.6f}"
    subtitle_path = output_path.with_suffix(".ass")
    _write_ass(subtitle_path, duration)
    subprocess.run(  # nosec B603
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x182033:s=720x1280:r=25:d={duration_text}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=48000:duration={duration_text}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    probe = _probe(ffprobe, output_path)
    streams = {item["codec_type"]: item for item in probe["streams"]}
    version = subprocess.run(  # nosec B603
        [ffmpeg, "-version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    return PreviewResult(
        output_path,
        subtitle_path,
        duration,
        str(streams["video"]["codec_name"]),
        str(streams["audio"]["codec_name"]),
        int(streams["video"]["width"]),
        int(streams["video"]["height"]),
        version,
    )
