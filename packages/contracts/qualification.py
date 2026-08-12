"""Production qualification is evidence, never an implicit capability promotion."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import ActorKind, ActorRef, ArtifactRef, StableName


class QualificationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NOT_EVALUATED = "not_evaluated"


class QualificationDecision(StrEnum):
    PENDING_HUMAN = "pending_human"
    APPROVED = "approved"
    REJECTED = "rejected"


class QualificationCheck(StrictContract):
    check_id: StableName
    dimension: StableName
    status: QualificationStatus
    blocker: bool
    detail: Annotated[str, Field(min_length=1, max_length=4_096)]
    evidence_paths: tuple[Annotated[str, Field(min_length=1, max_length=1_024)], ...] = ()

    @model_validator(mode="after")
    def enforce_blocker_status(self) -> Self:
        if self.blocker and self.status is QualificationStatus.PASSED:
            raise ValueError("passed qualification checks cannot remain blockers")
        return self


class ProductionQualification(StrictContract):
    release_slice: StableName
    resource_profile_ref: ArtifactRef
    code_revision: Annotated[str, Field(min_length=1, max_length=128)]
    checks: tuple[QualificationCheck, ...]
    automation_level: Annotated[str, Field(pattern=r"^L[0-4]$")]
    confidence_shadow: bool
    fact_story_created: bool
    engineering_recommendation: QualificationDecision
    decision: QualificationDecision
    approved_by: ActorRef | None = None

    @model_validator(mode="after")
    def enforce_human_approval_and_scope(self) -> Self:
        if not self.checks:
            raise ValueError("production qualification requires checks")
        ids = [check.check_id for check in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("qualification check ids must be unique")
        if not self.confidence_shadow or self.automation_level != "L1":
            raise ValueError("E06 qualification must preserve L1 and Confidence Shadow")
        if self.fact_story_created:
            raise ValueError("E06 qualification cannot create Fact or Story")
        if self.decision is QualificationDecision.APPROVED:
            if any(check.status is not QualificationStatus.PASSED for check in self.checks):
                raise ValueError("production approval requires every check to pass")
            if self.approved_by is None or self.approved_by.kind is not ActorKind.HUMAN:
                raise ValueError("production approval requires a human approver")
        elif self.approved_by is not None:
            raise ValueError("only approved qualification may carry approved_by")
        return self
