"""Deterministic E10/K02 voice take selection (provider-neutral).

Selects the best candidate take per narration line from a bounded candidate
set. Fail-closed: takes with unresolved pronunciation or QC findings are never
selected; when no take survives, the line is marked UNAVAILABLE and the set is
incomplete. Selection itself carries no TTS-provider dependency, so this can be
implemented and qualified before any real synthesis provider is admitted.
"""

from __future__ import annotations

from packages.contracts import ArtifactRef
from packages.contracts.media_production import (
    TakeDisposition,
    VoiceTake,
    VoiceTakeSet,
)
from packages.contracts.timeline_intent import NarrationLineSet

__all__ = ["SelectTakeConflict", "select_best_takes"]


class SelectTakeConflict(RuntimeError):
    """Raised when the take set cannot be derived from the given input."""


def _take_blocks(take: VoiceTake) -> tuple[str, ...]:
    """Return findings that make a take ineligible for selection."""
    blockers: list[str] = []
    for code in (*take.pronunciation_findings, *take.qc_findings):
        if code not in blockers:
            blockers.append(code)
    return tuple(blockers)


def _candidates_by_line(takes: tuple[VoiceTake, ...]) -> dict[object, list[VoiceTake]]:
    by_line: dict[object, list[VoiceTake]] = {}
    for take in takes:
        if take.disposition is not TakeDisposition.CANDIDATE:
            continue
        by_line.setdefault(take.narration_line_id, []).append(take)
    return by_line


def _closest_duration(candidates: list[VoiceTake], target_us: int) -> VoiceTake:
    """Pick the candidate whose measured duration is closest to the target."""
    scored = [
        (
            abs(take.duration.seconds * 1_000_000 - target_us) if take.duration else float("inf"),
            str(take.take_id),
            take,
        )
        for take in candidates
    ]
    scored.sort(key=lambda item: (item[0], item[1]))
    return scored[0][2]


def select_best_takes(
    *,
    narration: NarrationLineSet,
    narration_line_set_ref: ArtifactRef,
    takes: tuple[VoiceTake, ...],
    voice_profile_ref: ArtifactRef,
    max_takes_per_line: int = 3,
) -> VoiceTakeSet:
    """Select the best eligible candidate take for each narration line.

    Rules (fail-closed, deterministic):
    - only CANDIDATE takes participate; SELECTED/REJECTED/UNAVAILABLE are ignored
    - a take with any pronunciation or QC finding is ineligible
    - a take without committed audio or positive duration is ineligible
    - among eligible candidates pick the one whose duration is closest to the
      line target; ties resolve by take id for determinism
    - a line with no eligible candidate is left unselected and the set is
      marked incomplete
    """
    if max_takes_per_line < 1:
        raise SelectTakeConflict("max_takes_per_line must be positive")
    if not narration.lines:
        raise SelectTakeConflict("narration line set is empty")

    by_line = _candidates_by_line(takes)
    selected: list[VoiceTake] = []
    for line in narration.lines:
        candidates = by_line.get(line.line_id, ())
        eligible = [
            take
            for take in candidates
            if not _take_blocks(take)
            and take.audio_blob_ref is not None
            and take.duration is not None
            and take.duration.value > 0
        ]
        if not eligible:
            continue
        target_us = int(line.target_duration.seconds * 1_000_000)
        best = _closest_duration(eligible, target_us)
        selected.append(best.model_copy(update={"disposition": TakeDisposition.SELECTED}))

    selected_ids = {take.take_id for take in selected}
    rest: list[VoiceTake] = []
    preselected_line_ids: set[object] = set()
    for take in takes:
        if take.take_id in selected_ids:
            continue
        if take.disposition is TakeDisposition.SELECTED:
            # Already-selected takes from an earlier stage are kept as-is and
            # count as coverage for their line.
            rest.append(take)
            preselected_line_ids.add(take.narration_line_id)
        elif take.disposition is TakeDisposition.CANDIDATE:
            rest.append(take.model_copy(update={"disposition": TakeDisposition.REJECTED}))
        else:
            rest.append(take)

    selected_line_ids = {take.narration_line_id for take in selected} | preselected_line_ids
    incomplete = any(line.line_id not in selected_line_ids for line in narration.lines)
    return VoiceTakeSet(
        narration_line_set_ref=narration_line_set_ref,
        voice_profile_ref=voice_profile_ref,
        takes=tuple(selected + rest),
        max_takes_per_line=max_takes_per_line,
        incomplete=incomplete,
    )
