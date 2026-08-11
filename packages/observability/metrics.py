"""Bounded metric names and label policy for foundation workflows."""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED_LABELS = frozenset({"environment", "stage", "state", "queue", "error_type", "gate"})
PROHIBITED_LABELS = frozenset({"project_id", "run_id", "artifact_id", "workflow_id", "trace_id"})


@dataclass(frozen=True, slots=True)
class MetricPoint:
    name: str
    value: int | float
    labels: dict[str, str]

    def __post_init__(self) -> None:
        unknown = set(self.labels) - ALLOWED_LABELS
        if unknown:
            raise ValueError(f"high-cardinality or unknown metric labels: {sorted(unknown)}")
