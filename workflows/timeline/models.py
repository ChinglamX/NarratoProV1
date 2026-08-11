"""Small payloads for the fake Timeline-to-Preview durable workflow."""

from __future__ import annotations

from dataclasses import dataclass

from workflows.project.models import ArtifactPointer


@dataclass(frozen=True)
class PreviewWorkflowInput:
    run_id: str
    project_id: str
    trace_id: str
    timeline: ArtifactPointer
    profile: ArtifactPointer
    output_path: str


@dataclass(frozen=True)
class PreviewActivityResult:
    preview: ArtifactPointer
    subtitle_path: str
    qc: dict[str, str | int]


@dataclass
class PreviewWorkflowStatus:
    run_id: str
    state: str
    preview: ArtifactPointer | None = None
    active_review_id: str | None = None
