"""Evidence-grounded retrieval, sequence continuity and deterministic reframe planning."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from packages.contracts import ArtifactRef, RationalTime
from packages.contracts.timeline_intent import (
    ClipCandidate,
    ClipRetrievalQuery,
    ClipSelection,
    ClipSelectionPlan,
    CompositionTarget,
    ContinuityReport,
    ContinuityRisk,
    CropKeyframe,
    CropPath,
    NarrativeBeatGraph,
    SourceSubtitleHandlingPlan,
    SourceSubtitlePolicy,
)


class ClipIndexPort(Protocol):
    """Replaceable Media/Fact index boundary; adapters never own selection policy."""

    def retrieve(self, query: ClipRetrievalQuery) -> Sequence[ClipCandidate]: ...


@dataclass(frozen=True, slots=True)
class VisualPlanningPolicy:
    continuity_penalty: float = 0.35
    repeated_source_penalty: float = 1.0
    crop_width: float = 0.5625
    crop_height: float = 1.0
    crop_dead_zone: float = 0.04
    maximum_crop_step: float = 0.12
    fallback: str = "background_fill"


DEFAULT_VISUAL_POLICY = VisualPlanningPolicy()


def retrieve_candidates(
    *, queries: Sequence[ClipRetrievalQuery], index: ClipIndexPort
) -> tuple[ClipCandidate, ...]:
    """Merge route results deterministically while rejecting ungrounded/mismatched results."""

    merged: dict[UUID, ClipCandidate] = {}
    for query in queries:
        for candidate in index.retrieve(query):
            if candidate.beat_id != query.beat_id:
                continue
            if not set(candidate.story_refs).intersection(query.story_refs):
                continue
            if query.required_character_refs and not set(query.required_character_refs).issubset(
                candidate.visible_character_refs
            ):
                continue
            previous = merged.get(candidate.candidate_id)
            if previous is None or _candidate_score(candidate) > _candidate_score(previous):
                merged[candidate.candidate_id] = candidate
    return tuple(sorted(merged.values(), key=lambda item: str(item.candidate_id)))


def plan_clip_sequence(
    *,
    candidate_set_ref: ArtifactRef,
    beat_graph: NarrativeBeatGraph,
    candidates: Sequence[ClipCandidate],
    policy: VisualPlanningPolicy = DEFAULT_VISUAL_POLICY,
    pinned: Mapping[UUID, UUID] | None = None,
    banned: frozenset[UUID] = frozenset(),
) -> ClipSelectionPlan:
    """Choose a legal sequence globally; a locally strong but discontinuous clip can lose."""

    pinned = pinned or {}
    pools: list[list[ClipCandidate]] = []
    for beat in beat_graph.beats:
        pool = [
            candidate
            for candidate in candidates
            if candidate.beat_id == beat.beat_id
            and candidate.candidate_id not in banned
            and candidate.rights_allowed
            and candidate.story_refs
            and candidate.evidence_refs
        ]
        if beat.beat_id in pinned:
            pool = [item for item in pool if item.candidate_id == pinned[beat.beat_id]]
        if not pool:
            continue
        pools.append(sorted(pool, key=lambda item: str(item.candidate_id)))
    if len(pools) != len(beat_graph.beats):
        return ClipSelectionPlan(candidate_set_ref=candidate_set_ref, selections=())

    paths: dict[UUID, tuple[float, tuple[ClipCandidate, ...]]] = {
        item.candidate_id: (_candidate_score(item), (item,)) for item in pools[0]
    }
    for pool in pools[1:]:
        next_paths: dict[UUID, tuple[float, tuple[ClipCandidate, ...]]] = {}
        for current in pool:
            ranked = [
                (
                    score
                    + _candidate_score(current)
                    - _transition_penalty(path[-1], current, policy),
                    (*path, current),
                )
                for score, path in paths.values()
            ]
            next_paths[current.candidate_id] = max(
                ranked, key=lambda item: (item[0], tuple(str(x.candidate_id) for x in item[1]))
            )
        paths = next_paths
    _, selected = max(
        paths.values(), key=lambda item: (item[0], tuple(str(x.candidate_id) for x in item[1]))
    )
    selections = tuple(
        ClipSelection(
            beat_id=beat.beat_id,
            candidate_id=candidate.candidate_id,
            selected_range=candidate.source_range,
            rationale="global grounded sequence score with continuity penalties",
        )
        for beat, candidate in zip(beat_graph.beats, selected, strict=True)
    )
    return ClipSelectionPlan(candidate_set_ref=candidate_set_ref, selections=selections)


def analyze_continuity(
    *,
    selection_plan_ref: ArtifactRef,
    selections: ClipSelectionPlan,
    candidates: Sequence[ClipCandidate],
) -> ContinuityReport:
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    risks: list[ContinuityRisk] = []
    for left, right in zip(selections.selections, selections.selections[1:], strict=False):
        left_candidate, right_candidate = by_id[left.candidate_id], by_id[right.candidate_id]
        risks.extend(_continuity_risks(left_candidate, right_candidate))
    return ContinuityReport(
        selection_plan_ref=selection_plan_ref,
        risks=tuple(risks),
        checked_edges=max(0, len(selections.selections) - 1),
        blocker_count=sum(risk.blocker for risk in risks),
    )


def solve_crop_path(
    *,
    selection_plan_ref: ArtifactRef,
    candidate_id: UUID,
    targets: Sequence[CompositionTarget],
    duration: RationalTime,
    policy: VisualPlanningPolicy = DEFAULT_VISUAL_POLICY,
) -> CropPath:
    """Create a bounded, dead-zone-smoothed path or an explicit fallback."""

    if not targets:
        return CropPath(
            selection_plan_ref=selection_plan_ref,
            candidate_id=candidate_id,
            keyframes=(),
            fallback=policy.fallback,
            manual_required=True,
        )
    ordered = sorted(targets, key=lambda item: (item.start.seconds, -item.priority))
    keyframes: list[CropKeyframe] = []
    previous_x: float | None = None
    for target in ordered:
        desired = min(max(target.center_x - policy.crop_width / 2, 0.0), 1.0 - policy.crop_width)
        if previous_x is not None:
            delta = desired - previous_x
            if abs(delta) <= policy.crop_dead_zone:
                desired = previous_x
            else:
                desired = previous_x + max(
                    -policy.maximum_crop_step, min(policy.maximum_crop_step, delta)
                )
        keyframes.append(
            CropKeyframe(
                position=target.start,
                x=desired,
                y=0.0,
                width=policy.crop_width,
                height=policy.crop_height,
                locked=target.locked,
            )
        )
        previous_x = desired
    if keyframes[-1].position.seconds > duration.seconds:
        return CropPath(
            selection_plan_ref=selection_plan_ref,
            candidate_id=candidate_id,
            keyframes=(),
            fallback=policy.fallback,
            manual_required=True,
        )
    return CropPath(
        selection_plan_ref=selection_plan_ref,
        candidate_id=candidate_id,
        keyframes=tuple(keyframes),
    )


def choose_source_subtitle_policy(
    *,
    candidate_id: UUID,
    text_track_refs: tuple[UUID, ...],
    required_for_story: bool,
    crop_safe: bool,
) -> SourceSubtitleHandlingPlan:
    if not text_track_refs:
        policy, reason, human = SourceSubtitlePolicy.CROP_OUT, "no source subtitle track", False
    elif required_for_story:
        policy, reason, human = (
            SourceSubtitlePolicy.PRESERVE,
            "source text carries story evidence",
            True,
        )
    elif crop_safe:
        policy, reason, human = (
            SourceSubtitlePolicy.CROP_OUT,
            "crop excludes nonessential source text",
            False,
        )
    else:
        policy, reason, human = (
            SourceSubtitlePolicy.REPOSITION_CANVAS,
            "avoid destructive inpainting",
            True,
        )
    return SourceSubtitleHandlingPlan(
        candidate_id=candidate_id,
        policy=policy,
        source_text_track_refs=text_track_refs,
        rationale=reason,
        human_confirmation_required=human,
    )


def local_recompute_scope(beat_ids: Sequence[UUID], changed_beat_id: UUID) -> tuple[UUID, ...]:
    index = beat_ids.index(changed_beat_id)
    return tuple(beat_ids[max(0, index - 1) : min(len(beat_ids), index + 2)])


def _candidate_score(candidate: ClipCandidate) -> float:
    return sum(candidate.score_components.values())


def _transition_penalty(
    left: ClipCandidate, right: ClipCandidate, policy: VisualPlanningPolicy
) -> float:
    penalty = len(_continuity_risks(left, right)) * policy.continuity_penalty
    if left.source_ref == right.source_ref and left.source_range == right.source_range:
        penalty += policy.repeated_source_penalty
    return penalty


def _continuity_risks(left: ClipCandidate, right: ClipCandidate) -> list[ContinuityRisk]:
    risks: list[ContinuityRisk] = []
    checks = (
        ("screen_direction", "screen-direction-jump", 1, False),
        ("location", "location-discontinuity", 2, False),
        ("time", "time-order-conflict", 3, True),
        ("action_phase", "action-phase-jump", 2, False),
    )
    for field, code, severity, blocker in checks:
        left_value = left.continuity_features.get(field)
        right_value = right.continuity_features.get(field)
        if left_value is not None and right_value is not None and left_value != right_value:
            risks.append(
                ContinuityRisk(
                    left_candidate_id=left.candidate_id,
                    right_candidate_id=right.candidate_id,
                    risk_type=code,
                    severity=severity,
                    explanation=f"{field} changes from {left_value!s} to {right_value!s}",
                    blocker=blocker,
                )
            )
    return risks
