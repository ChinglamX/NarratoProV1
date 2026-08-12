"""Bounded Strategy Direction planning and deterministic constraint validation."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from packages.contracts import (
    ArtifactRef,
    SellingPointSet,
    StrategyCandidateSet,
    StrategyDirection,
)
from packages.contracts.strategy_candidates import CandidateBudget


class StrategyPlanningConflict(RuntimeError):
    pass


def build_strategy_candidate_set(
    *,
    approved_story_ref: ArtifactRef,
    selling_point_set_ref: ArtifactRef,
    effective_config_ref: ArtifactRef,
    selling_points: SellingPointSet,
    proposed: Sequence[StrategyDirection],
    known_story_refs: set[UUID],
    budget: CandidateBudget,
) -> StrategyCandidateSet:
    """Admit bounded typed proposals only when every structural ref is grounded."""

    known_points = {item.selling_point_id for item in selling_points.selling_points}
    admitted = []
    for candidate in proposed[: budget.max_strategy_directions]:
        point_refs = {
            *candidate.primary_selling_point_refs,
            *candidate.secondary_selling_point_refs,
        }
        if not point_refs <= known_points:
            raise StrategyPlanningConflict("strategy references unknown selling point")
        beat_refs = {ref for beat in candidate.narrative_spine for ref in beat.story_refs}
        if not beat_refs or not beat_refs <= known_story_refs:
            raise StrategyPlanningConflict("strategy narrative spine is not grounded in Story")
        admitted.append(candidate)
    if not admitted:
        raise StrategyPlanningConflict("no feasible strategy direction was admitted")
    return StrategyCandidateSet(
        approved_story_ref=approved_story_ref,
        selling_point_set_ref=selling_point_set_ref,
        effective_config_ref=effective_config_ref,
        candidates=tuple(admitted),
    )
