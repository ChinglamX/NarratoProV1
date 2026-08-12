"""Independent Strategy/Hook evaluation, diversity, risk, feasibility and cost contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import UUID, ArtifactRef, StableName
from packages.contracts.strategy_candidates import CandidateBlocker, CandidateDisposition


class RiskLikelihood(StrEnum):
    UNAVAILABLE = "unavailable"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrategyRisk(StrictContract):
    risk_id: UUID
    category: StableName
    severity: Annotated[int, Field(ge=0, le=3)]
    likelihood: RiskLikelihood
    basis: Annotated[str, Field(min_length=1, max_length=2_048)]
    mitigation: Annotated[str, Field(min_length=1, max_length=2_048)]
    owner: StableName
    gate_impact: Annotated[str, Field(pattern=r"^(none|warning|blocker)$")]


class CostEstimate(StrictContract):
    method_version: Annotated[str, Field(min_length=1, max_length=128)]
    resource_profile_ref: ArtifactRef
    minimum_micros: Annotated[int, Field(ge=0)]
    maximum_micros: Annotated[int, Field(ge=0)]
    estimated_review_seconds: Annotated[int, Field(ge=0)]
    components_micros: dict[StableName, Annotated[int, Field(ge=0)]]

    @model_validator(mode="after")
    def require_valid_range(self) -> Self:
        if self.maximum_micros < self.minimum_micros:
            raise ValueError("cost estimate maximum must not be below minimum")
        if sum(self.components_micros.values()) < self.minimum_micros:
            raise ValueError("cost components must support estimate minimum")
        return self


class FeasibilityReport(StrictContract):
    candidate_id: UUID
    feasible: bool
    source_coverage: Annotated[float, Field(ge=0.0, le=1.0)]
    duration_feasible: bool
    production_complexity: Annotated[int, Field(ge=0, le=3)]
    reasons: tuple[Annotated[str, Field(min_length=1, max_length=2_048)], ...] = ()


class CriticResult(StrictContract):
    critic_run_ref: ArtifactRef
    candidate_id: UUID
    prompt_ref: ArtifactRef
    provider_ref: ArtifactRef
    findings: tuple[CandidateBlocker, ...] = ()
    unavailable: bool = False


class CandidateEvaluation(StrictContract):
    candidate_id: UUID
    disposition: CandidateDisposition
    deterministic_blockers: tuple[CandidateBlocker, ...]
    critic_results: tuple[CriticResult, ...]
    risks: tuple[StrategyRisk, ...]
    feasibility: FeasibilityReport
    cost: CostEstimate
    heuristic_scores: dict[StableName, Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def blockers_dominate_scores(self) -> Self:
        critic_blockers = tuple(
            finding for result in self.critic_results for finding in result.findings
        )
        all_blockers = (*self.deterministic_blockers, *critic_blockers)
        if all_blockers and self.disposition is CandidateDisposition.VALID:
            raise ValueError("candidate blockers cannot be offset by scores")
        if not self.feasibility.feasible and self.disposition is CandidateDisposition.VALID:
            raise ValueError("infeasible candidate cannot be valid")
        return self


class DiversityPair(StrictContract):
    left_candidate_id: UUID
    right_candidate_id: UUID
    differing_dimensions: tuple[StableName, ...]
    duplicate: bool
    explanation: Annotated[str, Field(min_length=1, max_length=2_048)]

    @model_validator(mode="after")
    def reject_self_pair(self) -> Self:
        if self.left_candidate_id == self.right_candidate_id:
            raise ValueError("diversity pair cannot compare a candidate to itself")
        if self.duplicate and self.differing_dimensions:
            raise ValueError("duplicate pair cannot claim structural differences")
        return self


class DiversityReport(StrictContract):
    candidate_set_ref: ArtifactRef
    pairs: tuple[DiversityPair, ...]
    duplicate_clusters: tuple[tuple[UUID, ...], ...] = ()


class StrategyComparisonPackage(StrictContract):
    approved_story_ref: ArtifactRef
    effective_config_ref: ArtifactRef
    selling_point_set_ref: ArtifactRef
    strategy_candidate_set_ref: ArtifactRef
    hook_candidate_set_ref: ArtifactRef
    evaluation_refs: tuple[ArtifactRef, ...]
    evaluations: tuple[CandidateEvaluation, ...]
    diversity: DiversityReport
    blocker_candidate_ids: tuple[UUID, ...]
    incomplete: bool = False

    @model_validator(mode="after")
    def require_exact_candidate_coverage(self) -> Self:
        ids = [item.candidate_id for item in self.evaluations]
        if len(ids) != len(set(ids)):
            raise ValueError("comparison candidate evaluations must be unique")
        expected_blocked = {
            item.candidate_id
            for item in self.evaluations
            if item.disposition is not CandidateDisposition.VALID
        }
        if set(self.blocker_candidate_ids) != expected_blocked:
            raise ValueError("comparison blocker candidate ids must match evaluations")
        return self
