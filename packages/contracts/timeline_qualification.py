"""E09 engineering qualification separated from real craft-quality approval."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import ActorKind, ActorRef, StableName
from packages.contracts.qualification import QualificationCheck, QualificationDecision


class TimelineSevereError(StrictContract):
    code: StableName
    description: Annotated[str, Field(min_length=1, max_length=2_048)]
    blocks_timeline_approval: bool = True


class TimelineEngineeringQualification(StrictContract):
    release_slice: StableName
    code_revision: Annotated[str, Field(min_length=1, max_length=128)]
    checks: tuple[QualificationCheck, ...]
    severe_errors: tuple[TimelineSevereError, ...]
    automation_level: Annotated[str, Field(pattern=r"^L[0-4]$")]
    confidence_shadow: bool
    timeline_checkpoint_required: bool
    engineering_complete: bool
    production_decision: QualificationDecision
    approved_by: ActorRef | None = None

    @model_validator(mode="after")
    def enforce_boundary(self) -> Self:
        if not self.checks or not self.severe_errors:
            raise ValueError("timeline qualification requires checks and severe errors")
        if self.automation_level != "L1" or not self.confidence_shadow:
            raise ValueError("E09 qualification must retain L1 and Confidence Shadow")
        if not self.timeline_checkpoint_required:
            raise ValueError("E09 cannot bypass Timeline Checkpoint")
        if self.production_decision is QualificationDecision.APPROVED:
            if any(check.status.value != "passed" for check in self.checks):
                raise ValueError("production approval requires all checks passed")
            if self.approved_by is None or self.approved_by.kind is not ActorKind.HUMAN:
                raise ValueError("production approval requires human approver")
        elif self.approved_by is not None:
            raise ValueError("pending/rejected qualification cannot carry approver")
        return self
