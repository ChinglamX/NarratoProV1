"""Deterministic Strategy validation, structural diversity and comparison assembly."""

from __future__ import annotations

from itertools import combinations

from packages.contracts import ArtifactRef, StrategyCandidateSet, StrategyDirection
from packages.contracts.strategy_candidates import CandidateDisposition
from packages.contracts.strategy_evaluation import (
    CandidateEvaluation,
    DiversityPair,
    DiversityReport,
    StrategyComparisonPackage,
)


def structural_signature(candidate: StrategyDirection) -> tuple[object, ...]:
    return (
        candidate.primary_selling_point_refs,
        candidate.protagonist_ref,
        tuple(item.function for item in candidate.narrative_spine),
        tuple(item.information_owner for item in candidate.narrative_spine),
        tuple(sorted(candidate.reveal_policy.items())),
        candidate.target_duration.canonical_json(),
    )


def diversity_report(
    candidate_set_ref: ArtifactRef, candidate_set: StrategyCandidateSet
) -> DiversityReport:
    pairs = []
    duplicate_clusters = []
    for left, right in combinations(candidate_set.candidates, 2):
        dimensions = []
        if left.primary_selling_point_refs != right.primary_selling_point_refs:
            dimensions.append("primary_selling_point")
        if left.protagonist_ref != right.protagonist_ref:
            dimensions.append("viewpoint")
        if left.reveal_policy != right.reveal_policy:
            dimensions.append("reveal_policy")
        if tuple(item.function for item in left.narrative_spine) != tuple(
            item.function for item in right.narrative_spine
        ):
            dimensions.append("narrative_spine")
        duplicate = not dimensions
        if duplicate:
            duplicate_clusters.append((left.strategy_id, right.strategy_id))
        pairs.append(
            DiversityPair(
                left_candidate_id=left.strategy_id,
                right_candidate_id=right.strategy_id,
                differing_dimensions=tuple(dimensions),
                duplicate=duplicate,
                explanation=("No structural difference" if duplicate else ", ".join(dimensions)),
            )
        )
    return DiversityReport(
        candidate_set_ref=candidate_set_ref,
        pairs=tuple(pairs),
        duplicate_clusters=tuple(duplicate_clusters),
    )


def assemble_comparison(
    *,
    approved_story_ref: ArtifactRef,
    effective_config_ref: ArtifactRef,
    selling_point_set_ref: ArtifactRef,
    strategy_candidate_set_ref: ArtifactRef,
    hook_candidate_set_ref: ArtifactRef,
    candidate_set: StrategyCandidateSet,
    evaluation_refs: tuple[ArtifactRef, ...],
    evaluations: tuple[CandidateEvaluation, ...],
    incomplete: bool = False,
) -> StrategyComparisonPackage:
    report = diversity_report(strategy_candidate_set_ref, candidate_set)
    blocked = tuple(
        item.candidate_id
        for item in evaluations
        if item.disposition is not CandidateDisposition.VALID
    )
    return StrategyComparisonPackage(
        approved_story_ref=approved_story_ref,
        effective_config_ref=effective_config_ref,
        selling_point_set_ref=selling_point_set_ref,
        strategy_candidate_set_ref=strategy_candidate_set_ref,
        hook_candidate_set_ref=hook_candidate_set_ref,
        evaluation_refs=evaluation_refs,
        evaluations=evaluations,
        diversity=report,
        blocker_candidate_ids=blocked,
        incomplete=incomplete,
    )
