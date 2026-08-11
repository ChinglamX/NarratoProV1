"""Small deterministic payloads allowed in Temporal history."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArtifactPointer:
    artifact_id: str
    version: int
    artifact_type: str
    checksum: str | None = None


@dataclass(frozen=True)
class ActivityRequest:
    activity_id: str
    run_id: str
    trace_id: str
    stage: str
    execution_key: str
    inputs: tuple[ArtifactPointer, ...]
    config_snapshot: ArtifactPointer
    output_contract: str
    resource_requirement: dict[str, int | str | list[str]]


@dataclass(frozen=True)
class ActivityResult:
    execution_key: str
    outputs: tuple[ArtifactPointer, ...]
    metrics: dict[str, int | float]
    warnings: tuple[dict[str, str], ...] = ()


@dataclass(frozen=True)
class ReviewSignal:
    review_id: str
    target_version: int
    decision: str


@dataclass
class ProjectRunInput:
    run_id: str
    project_id: str
    trace_id: str
    effective_policy: ArtifactPointer
    resource_profile: ArtifactPointer
    config_snapshot: ArtifactPointer
    stages: tuple[str, ...] = ("foundation-conformance",)


@dataclass
class ProjectRunStatus:
    run_id: str
    state: str
    stage_states: dict[str, str] = field(default_factory=dict)
    active_review_id: str | None = None
    current_artifacts: dict[str, ArtifactPointer] = field(default_factory=dict)
    graph_version: int = 1
    cancel_requested: bool = False
