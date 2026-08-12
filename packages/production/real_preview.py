"""Media-grounded preview compiler for E09 J04.

Unlike :mod:`packages.production.fake_preview` (synthetic lavfi output), this
renderer compiles the actual Master Timeline from *real source media files*:
each VIDEO item is trimmed to its exact ``source_range``, scaled/padded to the
target frame, concatenated in timeline order, and muxed with the trimmed
original audio; SUBTITLE/NARRATION items are written to an ASS sidecar using
their declared safe areas. No creative content is synthesized.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
from fractions import Fraction
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from packages.contracts import MasterTimeline
from packages.contracts.timeline import TimelineItem, TimelineTrackKind
from packages.production.fake_preview import (
    PreviewRenderError,
    PreviewResult,
    _ass_timestamp,
    _probe,
)
from packages.timeline.validator import validate_timeline


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True)  # nosec B603
    if completed.returncode != 0:
        raise PreviewRenderError(
            "ffmpeg failed: " + (completed.stderr or "").strip().splitlines()[-1]
        )


def _video_items(timeline: MasterTimeline) -> list[TimelineItem]:
    for track in timeline.tracks:
        if track.kind == TimelineTrackKind.VIDEO:
            return [item for item in track.items if item.source_ref is not None]
    return []


def _audio_items(timeline: MasterTimeline) -> list[TimelineItem]:
    for track in timeline.tracks:
        if track.kind == TimelineTrackKind.ORIGINAL_AUDIO:
            return [item for item in track.items if item.source_ref is not None]
    return []


def _text_items(timeline: MasterTimeline, kind: TimelineTrackKind) -> list[TimelineItem]:
    for track in timeline.tracks:
        if track.kind == kind:
            return list(track.items)
    return []


def _seconds_text(value: Fraction) -> str:
    return f"{float(value):.6f}"


def _write_concat_file(path: Path, entries: list[str]) -> None:
    path.write_text("".join(f"file '{entry}'\n" for entry in entries), encoding="utf-8")


def _write_ass(
    path: Path,
    duration: Fraction,
    subtitle_items: list[TimelineItem],
    narration_items: list[TimelineItem],
) -> None:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 720",
        "PlayResY: 1280",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,"
        "BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,"
        "BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Default,Arial,44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,"
        "100,100,0,0,1,3,1,2,40,40,120,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    for item in [*subtitle_items, *narration_items]:
        text = str(item.parameters.get("text", "")).strip()
        if not text:
            continue
        start = item.timeline_range.start.seconds
        end = start + item.timeline_range.duration.seconds
        safe_area = cast(dict[str, Any], item.parameters.get("safe_area"))
        margin_v = 120
        if safe_area and all(key in safe_area for key in ("y", "height")):
            margin_v = round(
                max(0.0, 1.0 - float(safe_area["y"]) - float(safe_area["height"])) * 1280
            )
        escaped = text.replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},Default,,0,0,"
            f"{margin_v},,{escaped}"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def render_media_preview(
    timeline: MasterTimeline,
    source_paths: dict[UUID, Path],
    output_path: Path,
    *,
    target_width: int = 720,
    target_height: int = 1280,
    frame_rate: int = 25,
) -> PreviewResult:
    if not validate_timeline(timeline).render_ready:
        raise PreviewRenderError("timeline is not render-ready")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise PreviewRenderError("ffmpeg and ffprobe are required")
    video_items = _video_items(timeline)
    audio_items = _audio_items(timeline)
    if not video_items:
        raise PreviewRenderError("timeline has no grounded video items")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    work = output_path.parent / f".{output_path.stem}.work"
    work.mkdir(parents=True, exist_ok=True)

    clip_paths: list[Path] = []
    for index, item in enumerate(video_items):
        if item.source_ref is None:
            raise PreviewRenderError("video item has no source ref")
        if item.source_range is None:
            raise PreviewRenderError("video item has no source range")
        source = source_paths.get(item.source_ref.artifact_id)
        if source is None or not source.is_file():
            raise PreviewRenderError(f"source media unavailable: {item.source_ref.artifact_id}")
        clip = work / f"clip_{index:04d}.mp4"
        part = work / f"clip_{index:04d}.tmp.mp4"
        _run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(source),
                "-ss",
                _seconds_text(item.source_range.start.seconds),
                "-t",
                _seconds_text(item.source_range.duration.seconds),
                "-vf",
                (
                    f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                    f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
                    f"fps={frame_rate},setsar=1"
                ),
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(part),
            ]
        )
        os.replace(part, clip)
        clip_paths.append(clip)

    concat_file = work / "concat.txt"
    _write_concat_file(concat_file, [str(path) for path in clip_paths])
    video_path = work / "video.mp4"
    video_part = work / "video.tmp.mp4"
    _run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(video_part),
        ]
    )
    os.replace(video_part, video_path)

    audio_clips: list[Path] = []
    for index, item in enumerate(audio_items):
        if item.source_ref is None:
            raise PreviewRenderError("audio item has no source ref")
        if item.source_range is None:
            raise PreviewRenderError("audio item has no source range")
        source = source_paths.get(item.source_ref.artifact_id)
        if source is None or not source.is_file():
            raise PreviewRenderError(f"source media unavailable: {item.source_ref.artifact_id}")
        clip = work / f"audio_{index:04d}.m4a"
        part = work / f"audio_{index:04d}.tmp.m4a"
        _run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(source),
                "-ss",
                _seconds_text(item.source_range.start.seconds),
                "-t",
                _seconds_text(item.source_range.duration.seconds),
                "-vn",
                "-c:a",
                "aac",
                str(part),
            ]
        )
        os.replace(part, clip)
        audio_clips.append(clip)

    subtitle_path = output_path.with_suffix(".ass")
    _write_ass(
        subtitle_path,
        timeline.duration.seconds,
        _text_items(timeline, TimelineTrackKind.SUBTITLE),
        _text_items(timeline, TimelineTrackKind.NARRATION),
    )

    part = output_path.with_suffix(".tmp.mp4")
    if audio_clips:
        audio_concat = work / "audio_concat.txt"
        _write_concat_file(audio_concat, [str(path) for path in audio_clips])
        audio_path = work / "audio.m4a"
        _run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(audio_concat),
                "-c",
                "copy",
                str(audio_path),
            ]
        )
        _run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "copy",
                "-shortest",
                str(part),
            ]
        )
    else:
        _run([ffmpeg, "-y", "-i", str(video_path), "-c", "copy", str(part)])
    os.replace(part, output_path)

    probe = _probe(ffprobe, output_path)
    streams = {item["codec_type"]: item for item in probe["streams"]}
    version = subprocess.run(  # nosec B603
        [ffmpeg, "-version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    return PreviewResult(
        output_path=output_path,
        subtitle_path=subtitle_path,
        duration_seconds=timeline.duration.seconds,
        video_codec=str(streams["video"]["codec_name"]),
        audio_codec=str(streams["audio"]["codec_name"]) if "audio" in streams else "",
        width=int(streams["video"]["width"]),
        height=int(streams["video"]["height"]),
        ffmpeg_version=version,
    )
