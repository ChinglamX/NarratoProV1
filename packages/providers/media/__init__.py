"""Replaceable media probe, derivative and scene-detection providers."""

from packages.providers.media.ffmpeg import (
    DerivativeOutputs,
    FFmpegMediaProvider,
    ProbeResult,
    SourceTimeMap,
)
from packages.providers.media.scenes import SceneBoundary, detect_scenes

__all__ = [
    "DerivativeOutputs",
    "FFmpegMediaProvider",
    "ProbeResult",
    "SceneBoundary",
    "SourceTimeMap",
    "detect_scenes",
]
