"""Review decision domain rules independent from persistence and Temporal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReviewConflict(RuntimeError):
    pass


class ReviewForbidden(RuntimeError):
    pass


class ReviewGate(StrEnum):
    STORY = "story"
    STRATEGY = "strategy"
    TIMELINE = "timeline"
    RELEASE = "release"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class Reviewer:
    actor_id: str
    roles: frozenset[str]
    service_account: bool = False


def authorize_decision(gate: ReviewGate, reviewer: Reviewer) -> None:
    required_role = "release_approver" if gate is ReviewGate.RELEASE else "reviewer"
    if required_role not in reviewer.roles:
        raise ReviewForbidden(f"{required_role} role is required")
    if gate is ReviewGate.RELEASE and reviewer.service_account:
        raise ReviewForbidden("service accounts cannot approve release")


def validate_target(*, expected_version: int, actual_version: int, state: str) -> None:
    if state != "awaiting_review":
        raise ReviewConflict("review was already decided or is stale")
    if expected_version != actual_version:
        raise ReviewConflict("review target version is stale")
