"""Bounded Selling Point and Hook candidate-set contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import UUID, ArtifactRef, StableName
from packages.contracts.strategy import HookCandidate


class CandidateDisposition(StrEnum):
    VALID = "valid"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    NOT_SCHEDULED = "not_scheduled"


class CandidateBudget(StrictContract):
    max_selling_points: Annotated[int, Field(ge=1, le=100)]
    max_strategy_directions: Annotated[int, Field(ge=1, le=20)]
    max_hooks_per_direction: Annotated[int, Field(ge=1, le=20)]
    max_total_candidates: Annotated[int, Field(ge=1, le=500)]
    max_revision_rounds: Annotated[int, Field(ge=0, le=10)]
    max_model_tokens: Annotated[int, Field(ge=0, le=100_000_000)]
    max_estimated_cost_micros: Annotated[int, Field(ge=0, le=10**12)]

    @model_validator(mode="after")
    def require_global_bound(self) -> Self:
        product = self.max_strategy_directions * self.max_hooks_per_direction
        if product > self.max_total_candidates:
            raise ValueError("direction x hook budget exceeds global candidate bound")
        return self


class CandidateBlocker(StrictContract):
    code: StableName
    field: StableName
    detail: Annotated[str, Field(min_length=1, max_length=2_048)]
    story_ref: ArtifactRef | None = None


class CandidateValidation(StrictContract):
    candidate_id: UUID
    disposition: CandidateDisposition
    blockers: tuple[CandidateBlocker, ...] = ()
    warnings: tuple[Annotated[str, Field(min_length=1, max_length=2_048)], ...] = ()

    @model_validator(mode="after")
    def blocker_cannot_pass(self) -> Self:
        if self.blockers and self.disposition is CandidateDisposition.VALID:
            raise ValueError("candidate with blocker cannot be valid")
        return self


class SellingPointCoverage(StrictContract):
    story_ref_ids: tuple[UUID, ...]
    covered_story_ref_ids: tuple[UUID, ...]
    uncovered_story_ref_ids: tuple[UUID, ...]


class HookCandidateSet(StrictContract):
    approved_story_ref: ArtifactRef
    strategy_candidate_set_ref: ArtifactRef
    candidates: tuple[HookCandidate, ...]
    validations: tuple[CandidateValidation, ...]
    not_scheduled_mechanics: tuple[StableName, ...] = ()
    incomplete: bool = False

    @model_validator(mode="after")
    def require_unique_and_validated_candidates(self) -> Self:
        ids = [item.hook_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("hook candidate ids must be unique")
        validation_ids = {item.candidate_id for item in self.validations}
        if set(ids) != validation_ids:
            raise ValueError("every hook candidate requires exactly one validation")
        signatures = [
            (item.hook_type, item.source_moment_refs, item.continuation_beats)
            for item in self.candidates
        ]
        if len(signatures) != len(set(signatures)):
            raise ValueError("hook candidates must differ structurally")
        return self
