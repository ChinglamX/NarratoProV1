"""Structured provenance separating director judgment from tool execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class TaskType(StrEnum):
    SYSTEM_ENGINEERING = "TYPE_A"
    DRAMA_PRODUCTION = "TYPE_B"
    QUALITY_REVIEW = "TYPE_C"


class AgentRole(StrEnum):
    SYSTEM_ENGINEER = "AI System Engineer"
    DRAMA_PRODUCER = "AI Drama Producer"
    REVIEW_DIRECTOR = "AI Review Director"


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    description: str
    actor_role: AgentRole
    rationale: str
    manual_override: bool = False


@dataclass(frozen=True)
class ProductionRunProvenance:
    task_type: TaskType
    active_role: AgentRole
    auxiliary_roles: tuple[AgentRole, ...]
    director_decisions: tuple[DecisionRecord, ...]
    tool_generated_outputs: tuple[str, ...]
    human_corrections: tuple[str, ...]
    release_gate_status: str

    def __post_init__(self) -> None:
        expected = {
            TaskType.SYSTEM_ENGINEERING: AgentRole.SYSTEM_ENGINEER,
            TaskType.DRAMA_PRODUCTION: AgentRole.DRAMA_PRODUCER,
            TaskType.QUALITY_REVIEW: AgentRole.REVIEW_DIRECTOR,
        }[self.task_type]
        if self.active_role is not expected:
            raise ValueError("active role must match the task type")
        if self.active_role in self.auxiliary_roles:
            raise ValueError("active role cannot also be auxiliary")
        if self.release_gate_status not in {"not_requested", "awaiting_human", "human_released"}:
            raise ValueError("release gate status is invalid")
        if self.release_gate_status == "human_released" and not self.human_corrections:
            raise ValueError("human release requires recorded human evidence")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
