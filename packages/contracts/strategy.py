"""Canonical marketing strategy, selling-point, and hook contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.evidence import ConfidenceRecord, EvidenceLink, RiskClass
from packages.contracts.foundation import UUID, ArtifactRef, RationalTime, StableName

Text = Annotated[str, Field(min_length=1, max_length=8_192)]
Score = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]


class NarrativeRole(StrEnum):
    HOOK = "hook"
    CORE = "core"
    PAYOFF = "payoff"
    CONTEXT = "context"


class SellingPoint(StrictContract):
    selling_point_id: UUID
    taxonomy_type: StableName
    description: Text
    story_refs: tuple[UUID, ...]
    evidence: tuple[EvidenceLink, ...]
    audience_rationale: Text
    platform_fit: tuple[StableName, ...]
    narrative_role: NarrativeRole
    spoiler_level: Annotated[int, Field(ge=0, le=3)]
    required_context_refs: tuple[UUID, ...] = ()
    source_coverage: JsonObject
    risk_class: RiskClass
    heuristic_components: dict[StableName, Score]
    confidence: ConfidenceRecord
    assumptions: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def require_story_grounding(self) -> Self:
        if not self.story_refs or not self.evidence:
            raise ValueError("selling point requires story refs and evidence")
        return self


class SellingPointSet(StrictContract):
    approved_story_ref: ArtifactRef
    taxonomy_version: Annotated[str, Field(min_length=1, max_length=128)]
    selling_points: tuple[SellingPoint, ...]
    incomplete: bool = False

    @model_validator(mode="after")
    def require_unique_points(self) -> Self:
        ids = [item.selling_point_id for item in self.selling_points]
        if len(ids) != len(set(ids)):
            raise ValueError("selling point ids must be unique")
        return self


class NarrativeBeatIntent(StrictContract):
    beat_id: UUID
    function: StableName
    story_refs: tuple[UUID, ...]
    priority: Annotated[int, Field(ge=0, le=100)]
    information_owner: Annotated[str, Field(pattern=r"^(visual|dialogue|narration|mixed)$")]
    required: bool


class HookCandidate(StrictContract):
    hook_id: UUID
    hook_type: StableName
    opening_promise: Text
    source_moment_refs: tuple[UUID, ...]
    visual_intent: JsonObject
    narration_or_dialogue: Text | None = None
    audio_intent: JsonObject = Field(default_factory=dict)
    disclosed_information: tuple[Text, ...] = ()
    withheld_information: tuple[Text, ...] = ()
    audience_question: Text
    duration_budget: RationalTime
    continuation_beats: tuple[UUID, ...]
    evidence: tuple[EvidenceLink, ...]
    assumptions: tuple[Text, ...] = ()
    risks: tuple[StableName, ...] = ()
    heuristic_scores: dict[StableName, Score]
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def require_viable_hook(self) -> Self:
        if not self.source_moment_refs or not self.evidence:
            raise ValueError("hook requires source moments and evidence")
        if not self.continuation_beats:
            raise ValueError("hook requires a continuation plan")
        if self.duration_budget.value <= 0:
            raise ValueError("hook duration budget must be positive")
        return self


class StrategyDirection(StrictContract):
    strategy_id: UUID
    objective: Text
    audience_hypothesis: Text
    platform_profile_ref: ArtifactRef
    genre_config_ref: ArtifactRef
    primary_selling_point_refs: tuple[UUID, ...]
    secondary_selling_point_refs: tuple[UUID, ...] = ()
    protagonist_ref: UUID
    viewpoint: Text
    opening_promise: Text
    ending_payoff: Text
    narrative_spine: tuple[NarrativeBeatIntent, ...]
    reveal_policy: JsonObject
    emotional_curve_intent: tuple[StableName, ...]
    target_duration: RationalTime
    excluded_arc_refs: tuple[UUID, ...] = ()
    assumptions: tuple[Text, ...] = ()
    risks: tuple[StableName, ...] = ()
    production_estimate: JsonObject
    feasible: bool

    @model_validator(mode="after")
    def require_direction_structure(self) -> Self:
        if not self.primary_selling_point_refs:
            raise ValueError("strategy requires a primary selling point")
        if not self.narrative_spine:
            raise ValueError("strategy requires a narrative spine")
        if self.target_duration.value <= 0:
            raise ValueError("strategy target duration must be positive")
        return self


class StrategyCandidateSet(StrictContract):
    approved_story_ref: ArtifactRef
    selling_point_set_ref: ArtifactRef
    effective_config_ref: ArtifactRef
    candidates: tuple[StrategyDirection, ...]
    rejected_candidate_refs: tuple[ArtifactRef, ...] = ()

    @model_validator(mode="after")
    def require_structurally_distinct_candidates(self) -> Self:
        ids = [item.strategy_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("strategy ids must be unique")
        signatures = [
            (
                item.primary_selling_point_refs,
                item.protagonist_ref,
                tuple(beat.function for beat in item.narrative_spine),
            )
            for item in self.candidates
        ]
        if len(signatures) != len(set(signatures)):
            raise ValueError("strategy candidates must differ structurally")
        return self


class CreativeBrief(StrictContract):
    strategy_ref: ArtifactRef
    selected_strategy_id: UUID
    selected_hook_id: UUID
    target_duration: RationalTime
    narrative_spine: tuple[NarrativeBeatIntent, ...]
    hard_constraints: JsonObject
    soft_preferences: JsonObject
    approved_by_ref: StableName
