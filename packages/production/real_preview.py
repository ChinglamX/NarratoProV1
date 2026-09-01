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
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from packages.contracts import MasterTimeline
from packages.contracts.timeline import TimelineItem, TimelineTrackKind
from packages.production.fake_preview import (
    PreviewRenderError as PreviewRenderError,
)
from packages.production.fake_preview import (
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


def _frame_boundary(value: Fraction, frame_rate: int) -> int:
    """Resolve a timeline boundary once so per-clip rounding cannot accumulate."""

    return round(value * frame_rate)


def _assert_av_sync(probe: dict[str, Any], *, expected_duration: Fraction, frame_rate: int) -> None:
    streams = {item["codec_type"]: item for item in probe["streams"]}
    if "audio" not in streams:
        return
    expected = _frame_boundary(expected_duration, frame_rate) / frame_rate
    video_duration = float(streams["video"]["duration"])
    audio_duration = float(streams["audio"]["duration"])
    tolerance = 1 / frame_rate
    if (
        abs(video_duration - expected) > tolerance
        or abs(audio_duration - expected) > tolerance
        or abs(video_duration - audio_duration) > tolerance
    ):
        raise PreviewRenderError(
            "audio/video drift exceeds one frame: "
            f"expected={expected:.6f}s video={video_duration:.6f}s "
            f"audio={audio_duration:.6f}s"
        )


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
    progress: Callable[[int, int], None] | None = None,
) -> PreviewResult:
    """Render a media-grounded preview of the master timeline.

    ``progress(done, total)`` is invoked after each source clip is trimmed so
    long-running callers (e.g. Temporal activities with heartbeat timeouts) can
    report liveness during rendering.
    """
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
    render_end_frame = max(
        _frame_boundary(
            item.timeline_range.start.seconds + item.timeline_range.duration.seconds,
            frame_rate,
        )
        for item in video_items
    )
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
        start_frame = _frame_boundary(item.timeline_range.start.seconds, frame_rate)
        end_frame = _frame_boundary(
            item.timeline_range.start.seconds + item.timeline_range.duration.seconds,
            frame_rate,
        )
        frame_count = end_frame - start_frame
        if frame_count <= 0:
            raise PreviewRenderError("video item resolves to zero frames")
        _run(
            [
                ffmpeg,
                "-y",
                "-ss",
                _seconds_text(item.source_range.start.seconds),
                "-i",
                str(source),
                "-vf",
                (
                    f"trim=duration={_seconds_text(item.source_range.duration.seconds)},"
                    "setpts=PTS-STARTPTS,"
                    f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                    f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
                    f"fps={frame_rate},setsar=1,tpad=stop_mode=clone:stop_duration=1"
                ),
                "-an",
                "-frames:v",
                str(frame_count),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(part),
            ]
        )
        os.replace(part, clip)
        clip_paths.append(clip)
        if progress is not None:
            progress(index + 1, len(video_items))

    concat_file = work / "concat.txt"
    # ffmpeg's concat demuxer resolves entries relative to the concat file's
    # directory, not the process cwd; absolute entries keep relative output
    # paths (e.g. settings.temp_root="tmp") working.
    _write_concat_file(concat_file, [str(Path(path).resolve()) for path in clip_paths])
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
    audio_cursor_frame = 0
    for index, item in enumerate(audio_items):
        if item.source_ref is None:
            raise PreviewRenderError("audio item has no source ref")
        if item.source_range is None:
            raise PreviewRenderError("audio item has no source range")
        source = source_paths.get(item.source_ref.artifact_id)
        if source is None or not source.is_file():
            raise PreviewRenderError(f"source media unavailable: {item.source_ref.artifact_id}")
        start_frame = _frame_boundary(item.timeline_range.start.seconds, frame_rate)
        end_frame = _frame_boundary(
            item.timeline_range.start.seconds + item.timeline_range.duration.seconds,
            frame_rate,
        )
        if start_frame < audio_cursor_frame:
            raise PreviewRenderError("overlapping original-audio items are unsupported")
        if start_frame > audio_cursor_frame:
            gap = work / f"audio_gap_{index:04d}.wav"
            _render_silence(
                ffmpeg,
                gap,
                Fraction(start_frame - audio_cursor_frame, frame_rate),
            )
            audio_clips.append(gap)
        clip = work / f"audio_{index:04d}.wav"
        part = work / f"audio_{index:04d}.tmp.wav"
        _run(
            [
                ffmpeg,
                "-y",
                "-ss",
                _seconds_text(item.source_range.start.seconds),
                "-i",
                str(source),
                "-t",
                _seconds_text(Fraction(end_frame - start_frame, frame_rate)),
                "-vn",
                "-af",
                (
                    f"atrim=duration={_seconds_text(item.source_range.duration.seconds)},"
                    "asetpts=PTS-STARTPTS,aresample=48000,apad"
                ),
                "-c:a",
                "pcm_s16le",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(part),
            ]
        )
        os.replace(part, clip)
        audio_clips.append(clip)
        audio_cursor_frame = end_frame
        if progress is not None:
            progress(len(video_items) + index + 1, len(video_items) + len(audio_items))

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
        _write_concat_file(audio_concat, [str(Path(path).resolve()) for path in audio_clips])
        if audio_cursor_frame < render_end_frame:
            gap = work / "audio_gap_final.wav"
            _render_silence(
                ffmpeg,
                gap,
                Fraction(render_end_frame - audio_cursor_frame, frame_rate),
            )
            audio_clips.append(gap)
            _write_concat_file(audio_concat, [str(Path(path).resolve()) for path in audio_clips])
        audio_path = work / "audio.wav"
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
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(part),
            ]
        )
    else:
        _run([ffmpeg, "-y", "-i", str(video_path), "-c", "copy", str(part)])
    os.replace(part, output_path)

    probe = _probe(ffprobe, output_path)
    _assert_av_sync(
        probe,
        expected_duration=Fraction(render_end_frame, frame_rate),
        frame_rate=frame_rate,
    )
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


def _render_silence(ffmpeg: str, path: Path, duration: Fraction) -> None:
    part = path.with_suffix(".tmp.wav")
    _run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-t",
            _seconds_text(duration),
            "-c:a",
            "pcm_s16le",
            str(part),
        ]
    )
    os.replace(part, path)


@dataclass(frozen=True, slots=True)
class PartialPreviewResult:
    """Result of a partial (time-range) preview render."""

    output_path: Path
    subtitle_path: Path
    original_start: float
    original_end: float
    duration_seconds: float
    clip_count: int
    ffmpeg_version: str


def compute_changed_ranges(
    before: MasterTimeline,
    after: MasterTimeline,
    *,
    min_segment_duration: float = 0.5,
    merge_gap: float = 1.0,
) -> tuple[tuple[float, float], ...]:
    """Compute timeline time ranges that differ between two versions.

    Used by partial preview to determine which segments need re-render.
    Ranges shorter than ``min_segment_duration`` are expanded. Ranges within
    ``merge_gap`` seconds of each other are merged.
    """
    old_items = {
        item.item_id: item
        for track in before.tracks
        if track.kind == TimelineTrackKind.VIDEO
        for item in track.items
    }
    ranges: list[tuple[float, float]] = []
    for track in after.tracks:
        if track.kind != TimelineTrackKind.VIDEO:
            continue
        for item in track.items:
            old = old_items.get(item.item_id)
            if old is None or old != item:
                start = float(item.timeline_range.start.seconds)
                end = start + float(item.timeline_range.duration.seconds)
                ranges.append((start, end))
    if not ranges:
        return ()
    # Expand very short segments
    expanded = [
        (
            max(0.0, start),
            end if (end - start) >= min_segment_duration else start + min_segment_duration,
        )
        for start, end in ranges
    ]
    expanded.sort()
    merged: list[tuple[float, float]] = [expanded[0]]
    for start, end in expanded[1:]:
        last_start, last_end = merged[-1]
        if start - last_end <= merge_gap:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return tuple(merged)


def render_partial_preview(
    timeline: MasterTimeline,
    source_paths: dict[UUID, Path],
    output_path: Path,
    *,
    time_range: tuple[float, float],
    target_width: int = 720,
    target_height: int = 1280,
    frame_rate: int = 25,
) -> PartialPreviewResult:
    """Render only the portion of the timeline within ``time_range``.

    Video items overlapping the range are trimmed to the intersection and
    re-timed from zero. Subtitle/narration items within the range are included
    with adjusted timestamps. Items entirely outside the range are skipped.

    This is much faster than a full re-render when only a small edit was made.
    """
    if not validate_timeline(timeline).render_ready:
        raise PreviewRenderError("timeline is not render-ready")
    range_start, range_end = time_range
    if range_end <= range_start:
        raise PreviewRenderError("partial preview range must have positive duration")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        raise PreviewRenderError("ffmpeg and ffprobe are required")

    # Filter and re-time video items
    all_video = _video_items(timeline)
    selected: list[tuple[TimelineItem, float]] = []  # (item, new_start)
    cursor = 0.0
    for item in all_video:
        item_start = float(item.timeline_range.start.seconds)
        item_end = item_start + float(item.timeline_range.duration.seconds)
        if item_end <= range_start or item_start >= range_end:
            continue
        selected.append((item, cursor))
        overlap_start = max(item_start, range_start)
        overlap_end = min(item_end, range_end)
        cursor += overlap_end - overlap_start

    if not selected:
        raise PreviewRenderError(
            f"no video items overlap range [{range_start:.3f}, {range_end:.3f}]"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    work = output_path.parent / f".{output_path.stem}.partial.work"
    work.mkdir(parents=True, exist_ok=True)

    clip_paths: list[Path] = []
    for index, (item, _new_start) in enumerate(selected):
        if item.source_ref is None:
            raise PreviewRenderError("video item has no source ref")
        source = source_paths.get(item.source_ref.artifact_id)
        if source is None or not source.is_file():
            raise PreviewRenderError(f"source media unavailable: {item.source_ref.artifact_id}")
        item_start = float(item.timeline_range.start.seconds)
        item_end = item_start + float(item.timeline_range.duration.seconds)
        overlap_start = max(item_start, range_start)
        overlap_end = min(item_end, range_end)
        # Source range: shift by the item's offset into its source
        source_offset = float(item.source_range.start.seconds) if item.source_range else 0.0
        src_start = source_offset + (overlap_start - item_start)
        src_duration = overlap_end - overlap_start

        clip = work / f"clip_{index:04d}.mp4"
        # ffmpeg infers the container from the file extension; a trailing
        # ".part" would make it fail, so stage with ".tmp.mp4" and rename.
        part = clip.with_suffix(".tmp.mp4")
        _run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(source),
                "-ss",
                _seconds_text(Fraction(src_start)),
                "-t",
                _seconds_text(Fraction(src_duration)),
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
    _write_concat_file(concat_file, [str(Path(p).resolve()) for p in clip_paths])
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

    # Subtitles: include items within range, adjust timestamps
    subtitle_path = output_path.with_suffix(".ass")
    range_subtitles = [
        item
        for item in _text_items(timeline, TimelineTrackKind.SUBTITLE)
        if _item_overlaps(item, range_start, range_end)
    ]
    range_narration = [
        item
        for item in _text_items(timeline, TimelineTrackKind.NARRATION)
        if _item_overlaps(item, range_start, range_end)
    ]
    _write_partial_ass(
        subtitle_path,
        cursor,
        range_subtitles,
        range_narration,
        range_start=range_start,
    )

    part = output_path.with_suffix(".tmp.mp4")
    _run([ffmpeg, "-y", "-i", str(video_path), "-c", "copy", str(part)])
    os.replace(part, output_path)

    version = subprocess.run(  # nosec B603
        [ffmpeg, "-version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    return PartialPreviewResult(
        output_path=output_path,
        subtitle_path=subtitle_path,
        original_start=range_start,
        original_end=range_end,
        duration_seconds=cursor,
        clip_count=len(selected),
        ffmpeg_version=version,
    )


def _item_overlaps(item: TimelineItem, range_start: float, range_end: float) -> bool:
    start = item.timeline_range.start.seconds
    end = start + item.timeline_range.duration.seconds
    return end > range_start and start < range_end


def _write_partial_ass(
    path: Path,
    duration: float,
    subtitle_items: list[TimelineItem],
    narration_items: list[TimelineItem],
    *,
    range_start: float,
) -> None:
    """Write ASS subtitles for a partial preview, shifting timestamps to zero."""
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
        start = item.timeline_range.start.seconds - range_start
        end = start + item.timeline_range.duration.seconds
        start = max(0.0, start)
        end = min(duration, end)
        if end <= start:
            continue
        safe_area = cast(dict[str, Any], item.parameters.get("safe_area"))
        margin_v = 120
        if safe_area and all(key in safe_area for key in ("y", "height")):
            margin_v = round(
                max(0.0, 1.0 - float(safe_area["y"]) - float(safe_area["height"])) * 1280
            )
        escaped = text.replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_ass_timestamp(Fraction(start))},"
            f"{_ass_timestamp(Fraction(end))},Default,,0,0,{margin_v},,{escaped}"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
