"""Deterministic technical/shot benchmark extraction for the E09 reference demo."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, cast

from scenedetect import ContentDetector, SceneManager, open_video  # type: ignore[import-untyped]


class TimelineBenchmarkError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DemoBenchmark:
    benchmark_version: str
    source_path: str
    duration_seconds: float
    width: int
    height: int
    frame_rate: float
    video_codec: str
    audio_codec: str | None
    shot_count: int
    shot_duration_seconds: tuple[float, ...]
    unresolved_human_dimensions: tuple[str, ...]

    @property
    def median_shot_seconds(self) -> float:
        return median(self.shot_duration_seconds) if self.shot_duration_seconds else 0.0

    def document(self) -> dict[str, Any]:
        return {
            "benchmark_version": self.benchmark_version,
            "source_path": self.source_path,
            "technical_profile": {
                "duration_seconds": self.duration_seconds,
                "width": self.width,
                "height": self.height,
                "frame_rate": self.frame_rate,
                "video_codec": self.video_codec,
                "audio_codec": self.audio_codec,
            },
            "shot_profile": {
                "shot_count": self.shot_count,
                "median_shot_seconds": self.median_shot_seconds,
                "shot_duration_seconds": list(self.shot_duration_seconds),
            },
            "human_annotation_status": "pending",
            "unresolved_human_dimensions": list(self.unresolved_human_dimensions),
            "usage": "reference comparison only; never a universal creative template",
        }


def extract_demo_benchmark(
    source: Path, *, threshold: float = 27.0, benchmark_version: str = "e09-demo-v1"
) -> DemoBenchmark:
    if not source.is_file():
        raise TimelineBenchmarkError("demo source is unavailable")
    probe = _probe(source)
    video_stream = next((item for item in probe["streams"] if item["codec_type"] == "video"), None)
    if video_stream is None:
        raise TimelineBenchmarkError("demo has no video stream")
    audio_stream = next((item for item in probe["streams"] if item["codec_type"] == "audio"), None)
    video = open_video(str(source))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold))
    manager.detect_scenes(video, show_progress=False)
    scenes = manager.get_scene_list(start_in_scene=True)
    durations = tuple(round(end.get_seconds() - start.get_seconds(), 3) for start, end in scenes)
    return DemoBenchmark(
        benchmark_version=benchmark_version,
        source_path=str(source),
        duration_seconds=float(probe["format"]["duration"]),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        frame_rate=_rate(str(video_stream["r_frame_rate"])),
        video_codec=str(video_stream["codec_name"]),
        audio_codec=str(audio_stream["codec_name"]) if audio_stream else None,
        shot_count=len(durations),
        shot_duration_seconds=durations,
        unresolved_human_dimensions=(
            "hook-context-payoff",
            "performance-hold",
            "rhythm-tension-release",
            "narration-function-style",
            "composition-subtitle-packaging",
        ),
    )


def write_benchmark(benchmark: DemoBenchmark, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(benchmark.document(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output)


def _probe(source: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise TimelineBenchmarkError("ffprobe is unavailable")
    try:
        completed = subprocess.run(  # nosec B603
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
                "-of",
                "json",
                str(source),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise TimelineBenchmarkError("ffprobe failed") from error
    return cast(dict[str, Any], json.loads(completed.stdout))


def _rate(value: str) -> float:
    numerator, denominator = (int(item) for item in value.split("/", 1))
    return numerator / denominator if denominator else 0.0


def deterministic_parallel_signature(values: Sequence[str]) -> tuple[str, ...]:
    """Canonical fan-in ordering used by the J06 concurrency/replay probe."""
    return tuple(sorted(values))
