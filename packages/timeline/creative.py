"""Deterministic E09 planning constraints and Master Timeline intent assembly."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from packages.contracts import ArtifactRef, MasterTimeline, TimelineItem, TimelineTrack
from packages.contracts.timeline import TimelineLifecycle, TimelineTrackKind
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipCandidateSet,
    ClipSelection,
    ClipSelectionPlan,
    CoverageGap,
    NarrativeBeatGraph,
)


class CreativeTimelineConflict(RuntimeError):
    pass


def select_grounded_clips(
    *,
    candidate_set_ref: ArtifactRef,
    beat_graph: NarrativeBeatGraph,
    candidates: Sequence[ClipCandidate],
    pinned: dict[UUID, UUID] | None = None,
    banned: frozenset[UUID] = frozenset(),
) -> tuple[ClipCandidateSet, ClipSelectionPlan]:
    """Select one admissible candidate per beat; never fill coverage with unrelated material."""

    pinned = pinned or {}
    by_beat: dict[UUID, list[ClipCandidate]] = {beat.beat_id: [] for beat in beat_graph.beats}
    for candidate in candidates:
        if candidate.beat_id in by_beat:
            by_beat[candidate.beat_id].append(candidate)
    selections = []
    gaps = []
    for beat in beat_graph.beats:
        pool = [
            item
            for item in by_beat[beat.beat_id]
            if item.candidate_id not in banned and item.rights_allowed
        ]
        pinned_id = pinned.get(beat.beat_id)
        if pinned_id is not None:
            pool = [item for item in pool if item.candidate_id == pinned_id]
        if not pool:
            gaps.append(
                CoverageGap(
                    beat_id=beat.beat_id,
                    reason="no-grounded-usable-clip",
                    required_story_refs=beat.story_refs,
                )
            )
            continue
        selected = max(
            pool,
            key=lambda item: (
                sum(item.score_components.values()),
                -item.source_range.start.seconds,
                str(item.candidate_id),
            ),
        )
        selections.append(
            ClipSelection(
                beat_id=beat.beat_id,
                candidate_id=selected.candidate_id,
                selected_range=selected.source_range,
                rationale="highest admissible grounded composite score",
            )
        )
    candidate_set = ClipCandidateSet(
        beat_graph_ref=beat_graph.creative_brief_ref,
        candidates=tuple(candidates),
        coverage_gaps=tuple(gaps),
        incomplete=bool(gaps),
    )
    return candidate_set, ClipSelectionPlan(
        candidate_set_ref=candidate_set_ref,
        selections=tuple(selections),
    )


def assemble_intent_timeline(
    *,
    timeline_id: UUID,
    beat_graph: NarrativeBeatGraph,
    selections: ClipSelectionPlan,
    candidates: Sequence[ClipCandidate],
    dependencies: tuple[ArtifactRef, ...],
    track_id: UUID,
    item_ids: Sequence[UUID],
) -> MasterTimeline:
    if len(selections.selections) != len(beat_graph.beats):
        raise CreativeTimelineConflict("every beat requires a selected clip")
    if len(item_ids) != len(selections.selections):
        raise CreativeTimelineConflict("preallocated item IDs must match selections")
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    cursor = beat_graph.target_duration.model_copy(update={"value": 0})
    items = []
    for item_id, beat, selection in zip(
        item_ids, beat_graph.beats, selections.selections, strict=True
    ):
        candidate = by_id.get(selection.candidate_id)
        if candidate is None or selection.beat_id != beat.beat_id:
            raise CreativeTimelineConflict("selection does not match beat/candidate snapshot")
        duration = beat.target_duration
        items.append(
            TimelineItem.model_validate(
                {
                    "item_id": item_id,
                    "item_version": 1,
                    "item_type": "clip",
                    "timeline_range": {"start": cursor, "duration": duration},
                    "source_ref": candidate.source_ref,
                    "source_range": selection.selected_range,
                    "parameters": {"beat_id": str(beat.beat_id), "intent_state": "planned"},
                    "evidence_refs": candidate.evidence_refs,
                    "generation_dependencies": dependencies,
                }
            )
        )
        cursor = cursor.model_copy(update={"value": cursor.value + duration.value})
    return MasterTimeline(
        timeline_id=timeline_id,
        lifecycle=TimelineLifecycle.DRAFT,
        rate_num=beat_graph.target_duration.rate_num,
        rate_den=beat_graph.target_duration.rate_den,
        global_start=beat_graph.target_duration.model_copy(update={"value": 0}),
        duration=beat_graph.target_duration,
        tracks=(
            TimelineTrack(
                track_id=track_id,
                kind=TimelineTrackKind.VIDEO,
                order=0,
                items=tuple(items),
            ),
        ),
        dependencies=dependencies,
        metadata_namespace_version="e09-v1",
    )
