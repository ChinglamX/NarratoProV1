"""Small, replay-safe payloads for durable media ingest."""

from dataclasses import dataclass

from workflows.project.models import ArtifactPointer


@dataclass(frozen=True)
class MediaIngestWorkflowInput:
    project_id: str
    run_id: str
    trace_id: str
    source_path: str
    profile: ArtifactPointer
    profile_version: str
    rights: dict[str, str]


@dataclass(frozen=True)
class MediaIngestActivityResult:
    source: ArtifactPointer
    catalog: ArtifactPointer
    frame_plan: ArtifactPointer


@dataclass
class MediaIngestWorkflowStatus:
    run_id: str
    state: str
    source: ArtifactPointer | None = None
    catalog: ArtifactPointer | None = None
    active_review_id: str | None = None
