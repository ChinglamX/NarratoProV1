"""Deterministic E10 mix planning: timeline audio tracks -> MixStem set."""

from __future__ import annotations

from packages.contracts import ArtifactRef, MasterTimeline, MixPlan, MixStem, TimeRange
from packages.contracts.media_production import AudioRole
from packages.contracts.timeline import TimelineTrackKind


class MixPlanningConflict(RuntimeError):
    pass


def plan_mix_stems(
    timeline: MasterTimeline,
    *,
    conformed_timeline_ref: ArtifactRef,
    narration_source_ref: ArtifactRef,
    target_loudness_lufs: float,
    true_peak_ceiling_dbtp: float,
    measurement_profile_ref: ArtifactRef,
    duck_under_narration_db: float = -12.0,
) -> MixPlan:
    """Compile timeline audio tracks into an E10 MixPlan.

    ORIGINAL_AUDIO items become ORIGINAL stems; NARRATION items become one
    NARRATION stem (the voice asset). BGM/SFX stay absent until rights-cleared
    assets exist (ADR-049-style fail-closed). A MixPlan always requires a
    narration stem, enforced by the MixPlan contract.
    """
    stems: list[MixStem] = []
    for track in timeline.tracks:
        if track.kind is not TimelineTrackKind.ORIGINAL_AUDIO:
            continue
        for item in track.items:
            if item.source_ref is None or item.source_range is None:
                continue
            stems.append(
                MixStem(
                    role=AudioRole.ORIGINAL,
                    source_ref=item.source_ref,
                    timeline_range=item.timeline_range,
                )
            )
    # Narration stem references the produced voice asset (or its placeholder).
    stems.append(
        MixStem(
            role=AudioRole.NARRATION,
            source_ref=narration_source_ref,
            timeline_range=_narration_cover(timeline),
        )
    )
    return MixPlan(
        conformed_timeline_ref=conformed_timeline_ref,
        stems=tuple(stems),
        target_loudness_lufs=target_loudness_lufs,
        true_peak_ceiling_dbtp=true_peak_ceiling_dbtp,
        measurement_profile_ref=measurement_profile_ref,
    )


def _narration_cover(timeline: MasterTimeline) -> TimeRange:
    narration_ranges = [
        item.timeline_range
        for track in timeline.tracks
        if track.kind is TimelineTrackKind.NARRATION
        for item in track.items
    ]
    if not narration_ranges:
        raise MixPlanningConflict("timeline has no narration track to mix")
    start = min(item.start.seconds for item in narration_ranges)
    end = max(item.end_seconds for item in narration_ranges)
    reference = narration_ranges[0].start
    return TimeRange(
        start=reference.model_copy(
            update={"value": round(start * reference.rate_num / reference.rate_den)}
        ),
        duration=reference.model_copy(
            update={"value": round((end - start) * reference.rate_num / reference.rate_den)}
        ),
    )
