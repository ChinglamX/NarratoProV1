"""Deterministic E10/K05 subtitle collision detection (provider-neutral).

Detects timing and spatial collisions between subtitle cues on the primary
layer and against the safe area. Pure function over the typed cue set: it never
moves cues itself, it reports findings (e.g. ``temporal-overlap``,
``safe-area-violation``) so the caller can reflow or fail closed. Mirrors the
SubtitleCueSet primary-layer non-overlap invariant in report form.
"""

from __future__ import annotations

from itertools import pairwise

from packages.contracts.media_production import SubtitleCue

__all__ = ["SubtitleCollisionConflict", "detect_subtitle_collisions"]


class SubtitleCollisionConflict(RuntimeError):
    """Raised when collision detection input is malformed."""


def _safe_area_bounds(cue: SubtitleCue) -> tuple[float, float]:
    """Return (y_top, y_bottom) fractions of frame height for a cue's safe area.

    Defaults match the ASS renderer: y=0.8, height=0.14 (bottom band).
    """
    from typing import Any, cast

    safe = cue.safe_area or {}
    y = float(cast(Any, safe.get("y", 0.8)))
    height = float(cast(Any, safe.get("height", 0.14)))
    return (y, y + height)


def detect_subtitle_collisions(cues: tuple[SubtitleCue, ...]) -> tuple[str, ...]:
    """Return deterministic collision findings for a subtitle cue set.

    Checks:
    - temporal-overlap: two cues whose timeline ranges overlap on the primary
      layer (the contract forbids this, but a set constructed with the field
      default can still carry collisions from an external source)
    - safe-area-violation: a cue whose safe area falls outside [0, 1] or is
      inverted (y >= y+height)
    Findings are ordered and deduplicated for determinism.
    """
    findings: list[str] = []
    ordered = sorted(cues, key=lambda cue: cue.timeline_range.start.seconds)
    for left, right in pairwise(ordered):
        if left.timeline_range.end_seconds > right.timeline_range.start.seconds:
            finding = f"temporal-overlap:{left.cue_id}:{right.cue_id}"
            if finding not in findings:
                findings.append(finding)
    for cue in cues:
        top, bottom = _safe_area_bounds(cue)
        if not (0.0 <= top < bottom <= 1.0):
            finding = f"safe-area-violation:{cue.cue_id}"
            if finding not in findings:
                findings.append(finding)
    return tuple(sorted(findings))
