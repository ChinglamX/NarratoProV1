from dataclasses import dataclass

from workflows.project.models import ArtifactPointer


@dataclass(frozen=True)
class StoryReasoningInput:
    project_id: str
    run_id: str
    trace_id: str
    fact_set: ArtifactPointer
    identity_graph: ArtifactPointer
    config: ArtifactPointer
    resource_profile: ArtifactPointer
    event_set_artifact_id: str
    state_graph_artifact_id: str
    causal_graph_artifact_id: str
    story_graph_artifact_id: str


@dataclass(frozen=True)
class StoryStageResult:
    output: ArtifactPointer
    unresolved_count: int = 0


@dataclass
class StoryReasoningStatus:
    run_id: str
    state: str
    current_stage: str
    event_set: ArtifactPointer | None = None
    character_state_graph: ArtifactPointer | None = None
    causal_graph: ArtifactPointer | None = None
    story_graph: ArtifactPointer | None = None
