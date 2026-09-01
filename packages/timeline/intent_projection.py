"""Deterministic projections from planning products into J04 assembly intents.

These are mechanical derivations, not creative generation: original audio
follows the selected clips, and subtitle intents mirror the approved narration
lines with an explicit safe area. BGM/SFX stay absent until rights-cleared
assets are admitted.
"""

from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256
from uuid import UUID

from packages.contracts import ArtifactRef, RationalTime, TimeRange
from packages.contracts.timeline_intent import (
    AudioIntent,
    AudioIntentRole,
    ClipCandidate,
    ClipSelectionPlan,
    NarrationLineSet,
    SubtitleIntent,
)

DEFAULT_SUBTITLE_SAFE_AREA: dict[str, float] = {
    "x": 0.08,
    "y": 0.78,
    "width": 0.84,
    "height": 0.14,
}


def _deterministic_uuid4(key: str) -> UUID:
    """Deterministic v4-shaped UUID so replayed projections commit identically."""

    raw = bytearray(sha256(key.encode("utf-8")).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))


def project_original_audio_intents(
    selections: ClipSelectionPlan,
    candidates: Sequence[ClipCandidate],
) -> tuple[AudioIntent, ...]:
    """One ORIGINAL audio intent per selected clip, aligned to its timeline range."""

    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    cursor = RationalTime(value=0, rate_num=1_000_000)
    intents: list[AudioIntent] = []
    for selection in selections.selections:
        candidate = by_id.get(selection.candidate_id)
        if candidate is None or candidate.source_ref is None:
            continue
        duration = selection.selected_range.duration
        intents.append(
            AudioIntent(
                intent_id=_deterministic_uuid4(f"original-audio-intent:{selection.candidate_id}"),
                role=AudioIntentRole.ORIGINAL,
                timeline_range=TimeRange(start=cursor, duration=duration),
                source_ref=candidate.source_ref,
                source_range=selection.selected_range,
            )
        )
        cursor = cursor.model_copy(update={"value": cursor.value + duration.value})
    return tuple(intents)


def project_subtitle_intents_from_narration(
    narration: NarrationLineSet,
    style_ref: ArtifactRef,
    *,
    safe_area: dict[str, float] | None = None,
) -> tuple[SubtitleIntent, ...]:
    """Subtitle intents mirroring each narration line inside the declared safe area."""

    area = safe_area or DEFAULT_SUBTITLE_SAFE_AREA
    cursor = RationalTime(value=0, rate_num=1_000_000)
    intents: list[SubtitleIntent] = []
    for line in narration.lines:
        intents.append(
            SubtitleIntent(
                intent_id=_deterministic_uuid4(f"subtitle-intent:{line.line_id}"),
                line_id=line.line_id,
                timeline_range=TimeRange(start=cursor, duration=line.target_duration),
                text=line.text,
                style_ref=style_ref,
                safe_area=dict(area),
                evidence_refs=line.evidence_refs,
            )
        )
        cursor = cursor.model_copy(update={"value": cursor.value + line.target_duration.value})
    return tuple(intents)
