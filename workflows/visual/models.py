from dataclasses import dataclass

from workflows.project.models import ArtifactPointer


@dataclass(frozen=True)
class VisualWorkflowInput:
    project_id: str
    run_id: str
    trace_id: str
    source: ArtifactPointer
    frame_plan: ArtifactPointer
    frame: ArtifactPointer
    source_time_value: int
    source_time_rate_num: int
    config: ArtifactPointer
    resource_profile: ArtifactPointer
    local_frame_path: str
    raw_artifact_id: str
    observation_artifact_id: str
    allow_research: bool = False
    capability: str = "detection"


@dataclass(frozen=True)
class VisualActivityResult:
    raw_response: ArtifactPointer
    observation: ArtifactPointer


@dataclass
class VisualWorkflowStatus:
    run_id: str
    state: str
    raw_response: ArtifactPointer | None = None
    observation: ArtifactPointer | None = None
