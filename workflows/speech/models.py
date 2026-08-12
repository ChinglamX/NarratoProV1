from dataclasses import dataclass

from workflows.project.models import ArtifactPointer


@dataclass(frozen=True)
class SpeechWorkflowInput:
    project_id: str
    run_id: str
    trace_id: str
    source_audio: ArtifactPointer
    config: ArtifactPointer
    resource_profile: ArtifactPointer
    local_audio_path: str
    raw_artifact_id: str
    observation_artifact_id: str
    provider_base_url: str = "http://127.0.0.1:8000"
    provider_model: str = "sensevoice"
    allow_research: bool = False


@dataclass(frozen=True)
class SpeechActivityResult:
    raw_response: ArtifactPointer
    observation: ArtifactPointer


@dataclass
class SpeechWorkflowStatus:
    run_id: str
    state: str
    raw_response: ArtifactPointer | None = None
    observation: ArtifactPointer | None = None
