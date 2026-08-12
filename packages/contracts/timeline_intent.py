"""E09 creative timeline intent contracts grounded in an approved strategy boundary."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import UUID, ArtifactRef, RationalTime, StableName, TimeRange


class BeatFunction(StrEnum):
    HOOK = "hook"
    CONTEXT = "context"
    ESCALATION = "escalation"
    TURN = "turn"
    PAYOFF = "payoff"
    CTA = "cta"


class TimelineIntentInput(StrictContract):
    approved_creative_brief_ref: ArtifactRef
    approved_variant_plan_ref: ArtifactRef
    approved_story_ref: ArtifactRef
    media_catalog_ref: ArtifactRef
    platform_profile_ref: ArtifactRef

    @model_validator(mode="after")
    def require_approved_boundary_types(self) -> Self:
        expected = (
            (self.approved_creative_brief_ref, "CreativeBrief"),
            (self.approved_variant_plan_ref, "VariantPlan"),
            (self.approved_story_ref, "StoryGraph"),
            (self.media_catalog_ref, "EpisodeCatalog"),
        )
        if any(reference.artifact_type != kind for reference, kind in expected):
            raise ValueError("timeline intent input requires approved typed boundaries")
        return self


class NarrativeBeat(StrictContract):
    beat_id: UUID
    function: BeatFunction
    story_refs: tuple[UUID, ...]
    target_duration: RationalTime
    minimum_duration: RationalTime
    maximum_duration: RationalTime
    required_information: tuple[Annotated[str, Field(min_length=1, max_length=1_024)], ...]
    emotional_intent: JsonObject
    locked: bool = False

    @model_validator(mode="after")
    def validate_budget(self) -> Self:
        minimum = self.minimum_duration.seconds
        target = self.target_duration.seconds
        maximum = self.maximum_duration.seconds
        if not self.story_refs or not self.required_information:
            raise ValueError("narrative beat must be grounded and informative")
        if minimum <= 0 or not minimum <= target <= maximum:
            raise ValueError("beat duration must satisfy positive min <= target <= max")
        return self


class NarrativeBeatGraph(StrictContract):
    creative_brief_ref: ArtifactRef
    beats: tuple[NarrativeBeat, ...]
    target_duration: RationalTime

    @model_validator(mode="after")
    def validate_graph_budget(self) -> Self:
        if not self.beats or len({beat.beat_id for beat in self.beats}) != len(self.beats):
            raise ValueError("beat graph requires unique beats")
        if sum(beat.minimum_duration.seconds for beat in self.beats) > self.target_duration.seconds:
            raise ValueError("minimum beat budget exceeds target duration")
        return self


class ClipCandidate(StrictContract):
    candidate_id: UUID
    beat_id: UUID
    source_ref: ArtifactRef
    source_range: TimeRange
    story_refs: tuple[UUID, ...]
    evidence_refs: tuple[UUID, ...]
    visible_character_refs: tuple[UUID, ...] = ()
    quality: JsonObject
    continuity_features: JsonObject
    reframe_feasible: bool
    rights_allowed: bool
    score_components: dict[StableName, Annotated[float, Field(ge=0.0, le=1.0)]]

    @model_validator(mode="after")
    def require_grounded_usable_source(self) -> Self:
        if self.source_range.is_empty or not self.story_refs or not self.evidence_refs:
            raise ValueError("clip candidate requires source duration, Story and Evidence")
        return self


class CoverageGap(StrictContract):
    beat_id: UUID
    reason: StableName
    required_story_refs: tuple[UUID, ...]
    blocker: bool = True


class ClipCandidateSet(StrictContract):
    beat_graph_ref: ArtifactRef
    candidates: tuple[ClipCandidate, ...]
    coverage_gaps: tuple[CoverageGap, ...] = ()
    incomplete: bool = False

    @model_validator(mode="after")
    def reject_duplicate_candidates(self) -> Self:
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("clip candidate ids must be unique")
        if self.coverage_gaps and not self.incomplete:
            raise ValueError("coverage gaps require incomplete state")
        return self


class ClipSelection(StrictContract):
    beat_id: UUID
    candidate_id: UUID
    selected_range: TimeRange
    rationale: Annotated[str, Field(min_length=1, max_length=2_048)]
    continuity_waivers: tuple[StableName, ...] = ()


class ContinuityRisk(StrictContract):
    left_candidate_id: UUID
    right_candidate_id: UUID
    risk_type: StableName
    severity: Annotated[int, Field(ge=0, le=3)]
    explanation: Annotated[str, Field(min_length=1, max_length=2_048)]
    blocker: bool = False


class ClipSelectionPlan(StrictContract):
    candidate_set_ref: ArtifactRef
    selections: tuple[ClipSelection, ...]
    continuity_risks: tuple[ContinuityRisk, ...] = ()


class RetrievalRoute(StrEnum):
    EVIDENCE = "evidence"
    CHARACTER = "character"
    NEIGHBORHOOD = "neighborhood"
    SEMANTIC = "semantic"
    HUMAN_PIN = "human_pin"


class ClipRetrievalQuery(StrictContract):
    beat_id: UUID
    story_refs: tuple[UUID, ...]
    required_character_refs: tuple[UUID, ...] = ()
    routes: tuple[RetrievalRoute, ...]
    top_k_per_route: Annotated[int, Field(ge=1, le=100)]

    @model_validator(mode="after")
    def require_grounded_routes(self) -> Self:
        if not self.story_refs or not self.routes:
            raise ValueError("clip retrieval query requires Story refs and routes")
        if len(set(self.routes)) != len(self.routes):
            raise ValueError("clip retrieval routes must be unique")
        return self


class ContinuityReport(StrictContract):
    selection_plan_ref: ArtifactRef
    risks: tuple[ContinuityRisk, ...]
    checked_edges: Annotated[int, Field(ge=0)]
    blocker_count: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def reconcile_blockers(self) -> Self:
        if self.blocker_count != sum(risk.blocker for risk in self.risks):
            raise ValueError("continuity blocker count must match risks")
        return self


class CompositionTarget(StrictContract):
    target_ref: UUID
    start: RationalTime
    end: RationalTime
    center_x: Annotated[float, Field(ge=0.0, le=1.0)]
    center_y: Annotated[float, Field(ge=0.0, le=1.0)]
    minimum_coverage: Annotated[float, Field(gt=0.0, le=1.0)]
    priority: Annotated[int, Field(ge=0, le=100)]
    locked: bool = False

    @model_validator(mode="after")
    def require_positive_window(self) -> Self:
        if self.end.seconds <= self.start.seconds:
            raise ValueError("composition target window must be positive")
        return self


class SourceSubtitlePolicy(StrEnum):
    PRESERVE = "preserve"
    CROP_OUT = "crop_out"
    MASK = "mask"
    REPOSITION_CANVAS = "reposition_canvas"
    MANUAL = "manual"


class SourceSubtitleHandlingPlan(StrictContract):
    candidate_id: UUID
    policy: SourceSubtitlePolicy
    source_text_track_refs: tuple[UUID, ...] = ()
    rationale: Annotated[str, Field(min_length=1, max_length=2_048)]
    human_confirmation_required: bool = False


class VisualPlanningReport(StrictContract):
    candidate_set_ref: ArtifactRef
    selection_plan_ref: ArtifactRef
    continuity_report_ref: ArtifactRef
    crop_path_refs: tuple[ArtifactRef, ...]
    subtitle_plan_refs: tuple[ArtifactRef, ...]
    blocker_codes: tuple[StableName, ...] = ()
    locally_recomputed_beat_ids: tuple[UUID, ...] = ()


class BeatRhythm(StrictContract):
    beat_id: UUID
    target_duration: RationalTime
    entry_energy: Annotated[float, Field(ge=0.0, le=1.0)]
    exit_energy: Annotated[float, Field(ge=0.0, le=1.0)]
    information_density: Annotated[float, Field(ge=0.0, le=1.0)]
    breathing_point: bool = False


class RhythmPlan(StrictContract):
    beat_graph_ref: ArtifactRef
    selection_plan_ref: ArtifactRef
    beats: tuple[BeatRhythm, ...]
    target_duration: RationalTime
    unresolved_conflicts: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def reconcile_duration(self) -> Self:
        if not self.beats:
            raise ValueError("rhythm plan requires beats")
        total = sum(item.target_duration.seconds for item in self.beats)
        if total != self.target_duration.seconds:
            raise ValueError("rhythm beat durations must equal target duration")
        return self


class DurationConflict(StrictContract):
    minimum_required: RationalTime
    available: RationalTime
    affected_beat_ids: tuple[UUID, ...]
    alternatives: tuple[StableName, ...]
    blocker: bool = True


class NarrationFinding(StrictContract):
    line_id: UUID
    code: StableName
    explanation: Annotated[str, Field(min_length=1, max_length=2_048)]
    blocker: bool


class NarrationPlanningReport(StrictContract):
    line_set_ref: ArtifactRef
    findings: tuple[NarrationFinding, ...]
    evidence_coverage: Annotated[float, Field(ge=0.0, le=1.0)]
    estimated_seconds: Annotated[float, Field(ge=0.0)]
    locked_line_ids: tuple[UUID, ...] = ()


class AudioIntentRole(StrEnum):
    ORIGINAL = "original"
    NARRATION = "narration"
    BGM = "bgm"
    SFX = "sfx"


class AudioIntent(StrictContract):
    intent_id: UUID
    role: AudioIntentRole
    timeline_range: TimeRange
    source_ref: ArtifactRef | None = None
    content_ref: StableName | None = None
    rights_ref: ArtifactRef | None = None
    duck_under_narration: bool = False
    gain_db: Annotated[float, Field(ge=-96.0, le=24.0)] = 0.0

    @model_validator(mode="after")
    def validate_audio_source(self) -> Self:
        if self.timeline_range.is_empty:
            raise ValueError("audio intent requires positive duration")
        if self.role is AudioIntentRole.ORIGINAL and self.source_ref is None:
            raise ValueError("original audio intent requires source ref")
        if self.role in {AudioIntentRole.BGM, AudioIntentRole.SFX} and (
            self.content_ref is None or self.rights_ref is None
        ):
            raise ValueError("BGM/SFX intent requires content and rights refs")
        if self.role is AudioIntentRole.BGM and not self.duck_under_narration:
            raise ValueError("BGM intent must declare narration ducking")
        return self


class SubtitleIntent(StrictContract):
    intent_id: UUID
    line_id: UUID
    timeline_range: TimeRange
    text: Annotated[str, Field(min_length=1, max_length=2_048)]
    style_ref: ArtifactRef
    safe_area: JsonObject
    evidence_refs: tuple[UUID, ...]

    @model_validator(mode="after")
    def require_safe_grounded_subtitle(self) -> Self:
        if self.timeline_range.is_empty or not self.evidence_refs:
            raise ValueError("subtitle intent requires duration and evidence")
        required = {"x", "y", "width", "height"}
        if not required.issubset(self.safe_area):
            raise ValueError("subtitle safe area requires normalized rectangle")
        return self


class OverlayIntent(StrictContract):
    intent_id: UUID
    timeline_range: TimeRange
    overlay_type: StableName
    content_ref: StableName
    style_ref: ArtifactRef
    safe_area: JsonObject


class AssemblyConflict(StrictContract):
    code: StableName
    owner: StableName
    affected_range: TimeRange
    explanation: Annotated[str, Field(min_length=1, max_length=2_048)]
    blocker: bool
    allowed_reflow_scope: Annotated[int, Field(ge=0, le=4)]


class TimelineAssemblyReport(StrictContract):
    timeline_ref: ArtifactRef | None = None
    track_kinds: tuple[StableName, ...]
    conflicts: tuple[AssemblyConflict, ...] = ()
    invalidated_artifact_types: tuple[StableName, ...] = ()
    revision_count: Annotated[int, Field(ge=0)] = 0
    revision_budget: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def enforce_revision_budget(self) -> Self:
        if self.revision_count > self.revision_budget:
            raise ValueError("assembly revision count exceeds budget")
        return self


class DialogueRelationship(StrEnum):
    COMPLEMENT = "complement"
    BRIDGE = "bridge"
    EMPHASIS = "emphasis"
    NONE = "none"


class NarrationLine(StrictContract):
    line_id: UUID
    beat_id: UUID
    text: Annotated[str, Field(min_length=1, max_length=2_048)]
    function: StableName
    story_refs: tuple[UUID, ...]
    evidence_refs: tuple[UUID, ...]
    target_duration: RationalTime
    dialogue_relationship: DialogueRelationship
    rhetorical: bool = False
    locked: bool = False

    @model_validator(mode="after")
    def require_evidence_for_factual_line(self) -> Self:
        if self.target_duration.value <= 0:
            raise ValueError("narration duration must be positive")
        if not self.rhetorical and (not self.story_refs or not self.evidence_refs):
            raise ValueError("factual narration requires Story and Evidence refs")
        return self


class NarrationLineSet(StrictContract):
    creative_brief_ref: ArtifactRef
    rhythm_plan_ref: ArtifactRef
    lines: tuple[NarrationLine, ...]
    estimated_duration: RationalTime
    redundancy_findings: tuple[StableName, ...] = ()
    unresolved_findings: tuple[StableName, ...] = ()


class CropKeyframe(StrictContract):
    position: RationalTime
    x: Annotated[float, Field(ge=0.0, le=1.0)]
    y: Annotated[float, Field(ge=0.0, le=1.0)]
    width: Annotated[float, Field(gt=0.0, le=1.0)]
    height: Annotated[float, Field(gt=0.0, le=1.0)]
    locked: bool = False

    @model_validator(mode="after")
    def remain_in_frame(self) -> Self:
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("crop keyframe must remain inside normalized frame")
        return self


class CropPath(StrictContract):
    selection_plan_ref: ArtifactRef
    candidate_id: UUID
    keyframes: tuple[CropKeyframe, ...]
    fallback: StableName | None = None
    manual_required: bool = False

    @model_validator(mode="after")
    def require_path_or_fallback(self) -> Self:
        if not self.keyframes and self.fallback is None:
            raise ValueError("crop path requires keyframes or explicit fallback")
        return self


class TimelineIntentPackage(StrictContract):
    input_ref: ArtifactRef
    beat_graph_ref: ArtifactRef
    clip_candidate_set_ref: ArtifactRef
    clip_selection_plan_ref: ArtifactRef
    crop_path_refs: tuple[ArtifactRef, ...]
    rhythm_plan_ref: ArtifactRef
    narration_line_set_ref: ArtifactRef
    master_timeline_ref: ArtifactRef
    blocker_codes: tuple[StableName, ...] = ()
    incomplete: bool = False
