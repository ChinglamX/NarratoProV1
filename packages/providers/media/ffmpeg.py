"""Pinned FFprobe/FFmpeg adapter with normalized contracts and atomic derivatives."""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import subprocess  # nosec B404
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

from packages.contracts import MediaTechnicalMetadata


class MediaProviderError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProbeResult:
    technical: MediaTechnicalMetadata
    raw: dict[str, Any]
    ffprobe_version: str


@dataclass(frozen=True, slots=True)
class SourceTimeMap:
    source_start_seconds: Fraction
    proxy_start_seconds: Fraction
    scale: Fraction
    max_error_seconds: Fraction

    def source_to_proxy(self, value: Fraction) -> Fraction:
        return self.proxy_start_seconds + (value - self.source_start_seconds) * self.scale

    def proxy_to_source(self, value: Fraction) -> Fraction:
        return self.source_start_seconds + (value - self.proxy_start_seconds) / self.scale


@dataclass(frozen=True, slots=True)
class DerivativeOutputs:
    proxy_path: Path
    audio_path: Path | None
    frame_directory: Path
    frame_paths: tuple[Path, ...]
    time_map: SourceTimeMap
    ffmpeg_version: str


def _fraction(value: str | None, *, default: Fraction = Fraction(0)) -> Fraction:
    if not value or value in {"N/A", "0/0"}:
        return default
    return Fraction(value)


def _time(seconds: Fraction) -> dict[str, int]:
    microseconds = seconds * 1_000_000
    if microseconds.denominator != 1:
        microseconds = Fraction(round(float(microseconds)), 1)
    return {"value": microseconds.numerator, "rate_num": 1_000_000}


class FFmpegMediaProvider:
    def __init__(self, *, ffprobe: str | None = None, ffmpeg: str | None = None) -> None:
        self.ffprobe = ffprobe or shutil.which("ffprobe") or ""
        self.ffmpeg = ffmpeg or shutil.which("ffmpeg") or ""
        if not self.ffprobe or not self.ffmpeg:
            raise MediaProviderError("ffprobe and ffmpeg are required")

    def probe(self, source: Path) -> ProbeResult:
        try:
            completed = subprocess.run(  # nosec B603
                [
                    self.ffprobe,
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    "-of",
                    "json",
                    str(source),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            raw = cast(dict[str, Any], json.loads(completed.stdout))
        except (subprocess.CalledProcessError, json.JSONDecodeError) as error:
            raise MediaProviderError("media is unreadable or unsupported") from error
        format_data = cast(dict[str, Any], raw.get("format", {}))
        duration = _fraction(str(format_data.get("duration", "")))
        start = _fraction(str(format_data.get("start_time", "0")))
        video_streams: list[dict[str, Any]] = []
        audio_streams: list[dict[str, Any]] = []
        for stream in cast(list[dict[str, Any]], raw.get("streams", [])):
            if stream.get("codec_type") == "video":
                average = _fraction(str(stream.get("avg_frame_rate", "")))
                nominal = _fraction(str(stream.get("r_frame_rate", "")))
                time_base = _fraction(str(stream.get("time_base", "")), default=Fraction(1, 1))
                rotation = int(stream.get("tags", {}).get("rotate", 0))
                for side_data in stream.get("side_data_list", []):
                    rotation = int(side_data.get("rotation", rotation))
                video_streams.append(
                    {
                        "stream_index": int(stream["index"]),
                        "codec": str(stream["codec_name"]),
                        "width": int(stream["width"]),
                        "height": int(stream["height"]),
                        "pixel_format": str(stream.get("pix_fmt", "unknown")),
                        "time_base_num": time_base.numerator,
                        "time_base_den": time_base.denominator,
                        "frame_rate_num": average.numerator if average else None,
                        "frame_rate_den": average.denominator if average else None,
                        "rotation_degrees": rotation,
                        "variable_frame_rate": bool(average and nominal and average != nominal),
                    }
                )
            elif stream.get("codec_type") == "audio":
                audio_streams.append(
                    {
                        "stream_index": int(stream["index"]),
                        "codec": str(stream["codec_name"]),
                        "sample_rate": int(stream["sample_rate"]),
                        "channels": int(stream["channels"]),
                        "channel_layout": stream.get("channel_layout"),
                    }
                )
        if not video_streams and not audio_streams:
            raise MediaProviderError("media contains no supported audio/video streams")
        mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        technical = MediaTechnicalMetadata.model_validate(
            {
                "duration": _time(duration),
                "start_time": _time(start),
                "format_name": str(format_data.get("format_name", "unknown")).split(",")[0],
                "mime_type": mime_type,
                "byte_size": source.stat().st_size,
                "video_streams": video_streams,
                "audio_streams": audio_streams,
            }
        )
        version = subprocess.run(  # nosec B603
            [self.ffprobe, "-version"], check=True, capture_output=True, text=True
        ).stdout.splitlines()[0]
        return ProbeResult(technical, raw, version)

    def derive(self, source: Path, output_directory: Path, probe: ProbeResult) -> DerivativeOutputs:
        output_directory.mkdir(parents=True, exist_ok=True)
        proxy = output_directory / "review_proxy.mp4"
        proxy_part = proxy.with_suffix(".mp4.part")
        command = [
            self.ffmpeg,
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-vf",
            "scale='min(720,iw)':-2",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            str(proxy_part),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)  # nosec B603
        os.replace(proxy_part, proxy)
        audio: Path | None = None
        if probe.technical.audio_streams:
            audio = output_directory / "speech_mono_16k.wav"
            part = audio.with_suffix(".wav.part")
            subprocess.run(  # nosec B603
                [
                    self.ffmpeg,
                    "-y",
                    "-i",
                    str(source),
                    "-map",
                    "0:a:0",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    "-f",
                    "wav",
                    str(part),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            os.replace(part, audio)
        frames = output_directory / "frames"
        frames.mkdir(exist_ok=True)
        subprocess.run(  # nosec B603
            [
                self.ffmpeg,
                "-y",
                "-i",
                str(source),
                "-vf",
                "fps=1/30,scale='min(720,iw)':-2",
                "-q:v",
                "3",
                str(frames / "frame_%05d.jpg"),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        frame_paths = tuple(sorted(frames.glob("frame_*.jpg")))
        version = subprocess.run(  # nosec B603
            [self.ffmpeg, "-version"], check=True, capture_output=True, text=True
        ).stdout.splitlines()[0]
        time_map = SourceTimeMap(
            probe.technical.start_time.seconds,
            Fraction(0),
            Fraction(1),
            Fraction(1, 1_000_000),
        )
        return DerivativeOutputs(proxy, audio, frames, frame_paths, time_map, version)
