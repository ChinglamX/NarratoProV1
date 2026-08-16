"""E10 media-production planning workflow models."""

from dataclasses import dataclass

from workflows.project.models import ArtifactPointer


@dataclass(frozen=True)
class MediaProductionPlanningInput:
    project_id: str
    run_id: str
    trace_id: str
    timeline: ArtifactPointer  # Approved MasterTimeline
    narration_line_set: ArtifactPointer
    voice_asset: ArtifactPointer | None = None  # None until TTS admitted
    mix_plan_id: str | None = None
    subtitle_cue_set_id: str | None = None
    ass_artifact_id: str | None = None
    style_profile: ArtifactPointer | None = None
    resource_profile: ArtifactPointer | None = None
    target_loudness_lufs: float = -14.0
    true_peak_ceiling_dbtp: float = -1.0


@dataclass(frozen=True)
class MediaProductionPlanningResult:
    mix_plan: ArtifactPointer
    subtitle_cue_set: ArtifactPointer
    ass_artifact: ArtifactPointer
    tts_pending: bool


@dataclass
class MediaProductionPlanningStatus:
    run_id: str
    state: str
    mix_plan: ArtifactPointer | None = None
    subtitle_cue_set: ArtifactPointer | None = None
    ass_artifact: ArtifactPointer | None = None
    tts_pending: bool = False
    blocked_codes: tuple[str, ...] = ()
