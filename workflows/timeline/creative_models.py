"""Serializable payloads for the E09 Creative Timeline durable workflow.

Plain dataclasses only: Temporal history must stay small and JSON-safe;
pydantic contracts are rebuilt inside activities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from workflows.project.models import ArtifactPointer


@dataclass(frozen=True)
class ClipQuerySpec:
    beat_id: str
    story_refs: tuple[str, ...]
    required_character_refs: tuple[str, ...]
    routes: tuple[str, ...]
    top_k_per_route: int


@dataclass(frozen=True)
class PlanningIdSpec:
    candidate_set_id: str
    selection_plan_id: str
    continuity_report_id: str
    visual_report_id: str
    crop_path_ids: dict[str, str] = field(default_factory=dict)
    subtitle_plan_ids: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualPlanningActivityRequest:
    run_id: str
    project_id: str
    trace_id: str
    resource_profile: ArtifactPointer
    beat_graph: ArtifactPointer
    candidate_sets: tuple[ArtifactPointer, ...]
    queries: tuple[ClipQuerySpec, ...]
    source_durations: dict[str, str] = field(default_factory=dict)
    ids: PlanningIdSpec | None = None


@dataclass(frozen=True)
class VisualPlanningActivityResult:
    candidate_set: ArtifactPointer
    selection_plan: ArtifactPointer
    continuity_report: ArtifactPointer
    visual_report: ArtifactPointer
    crop_paths: tuple[ArtifactPointer, ...]
    subtitle_plans: tuple[ArtifactPointer, ...]
    incomplete: bool


@dataclass(frozen=True)
class RhythmPlanningActivityRequest:
    run_id: str
    project_id: str
    trace_id: str
    resource_profile: ArtifactPointer
    beat_graph: ArtifactPointer
    selection_plan: ArtifactPointer
    rhythm_plan_id: str


@dataclass(frozen=True)
class RhythmPlanningActivityResult:
    rhythm_plan: ArtifactPointer | None
    conflict: dict[str, Any] | None


@dataclass(frozen=True)
class NarrationReviewActivityRequest:
    run_id: str
    project_id: str
    trace_id: str
    resource_profile: ArtifactPointer
    line_set: ArtifactPointer
    report_id: str
    dialogue_by_beat: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class NarrationReviewActivityResult:
    report: ArtifactPointer
    blocker_codes: tuple[str, ...]
    evidence_coverage: float


@dataclass(frozen=True)
class AssemblyActivityRequest:
    run_id: str
    project_id: str
    trace_id: str
    resource_profile: ArtifactPointer
    selection_plan: ArtifactPointer
    candidate_sets: tuple[ArtifactPointer, ...]
    line_set: ArtifactPointer | None
    subtitle_style: ArtifactPointer
    timeline_id: str
    master_timeline_id: str
    report_id: str
    track_ids: dict[str, str] = field(default_factory=dict)
    item_ids: tuple[str, ...] = ()
    duration: dict[str, int] | None = None


@dataclass(frozen=True)
class AssemblyActivityResult:
    master_timeline: ArtifactPointer | None
    report: ArtifactPointer
    blocked: bool
    conflict_codes: tuple[str, ...]


@dataclass(frozen=True)
class MediaPreviewActivityRequest:
    run_id: str
    project_id: str
    trace_id: str
    timeline: ArtifactPointer
    output_path: str
    target_width: int = 720
    target_height: int = 1280


@dataclass(frozen=True)
class MediaPreviewActivityResult:
    preview: ArtifactPointer
    subtitle_path: str
    qc: dict[str, str | int]


@dataclass(frozen=True)
class CreativeTimelineRequest:
    run_id: str
    project_id: str
    trace_id: str
    resource_profile: ArtifactPointer
    beat_graph: ArtifactPointer
    candidate_sets: tuple[ArtifactPointer, ...]
    queries: tuple[ClipQuerySpec, ...]
    planning: PlanningIdSpec
    rhythm_plan_id: str
    line_set: ArtifactPointer
    narration_report_id: str
    dialogue_by_beat: dict[str, list[str]]
    subtitle_style: ArtifactPointer
    timeline_id: str
    master_timeline_id: str
    assembly_report_id: str
    track_ids: dict[str, str]
    item_ids: tuple[str, ...]
    output_path: str
    source_durations: dict[str, str] = field(default_factory=dict)


@dataclass
class CreativeTimelineStatus:
    run_id: str
    state: str
    stage_states: dict[str, str] = field(default_factory=dict)
    active_review_id: str | None = None
    artifacts: dict[str, ArtifactPointer] = field(default_factory=dict)
    blocked_codes: tuple[str, ...] = ()
