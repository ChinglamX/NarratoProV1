"""PySceneDetect 0.7.1 shot-boundary baseline with explicit detector identity."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from scenedetect import AdaptiveDetector, detect  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class SceneBoundary:
    start_seconds: Fraction
    end_seconds: Fraction
    start_frame: int
    end_frame: int
    detector: str = "pyscenedetect-adaptive-0.7.1"


def detect_scenes(
    source: Path,
    *,
    adaptive_threshold: float = 3.0,
    min_scene_len: int = 15,
) -> tuple[SceneBoundary, ...]:
    scenes = detect(
        str(source),
        AdaptiveDetector(
            adaptive_threshold=adaptive_threshold,
            min_scene_len=min_scene_len,
        ),
        show_progress=False,
    )
    return tuple(
        SceneBoundary(
            Fraction(start.frame_num, 1) / Fraction(str(start.framerate)),
            Fraction(end.frame_num, 1) / Fraction(str(end.framerate)),
            start.frame_num,
            end.frame_num,
        )
        for start, end in scenes
    )
