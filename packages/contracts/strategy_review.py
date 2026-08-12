"""Exact Strategy Gate 2 package, selection, Creative Brief and bounded Variant Plan."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.envelopes import JsonObject
from packages.contracts.foundation import UUID, ArtifactRef, RationalTime, StableName
from packages.contracts.strategy import NarrativeBeatIntent


class StrategyReviewPackage(StrictContract):
    comparison_ref: ArtifactRef
    approved_story_ref: ArtifactRef
    effective_config_ref: ArtifactRef
    strategy_candidate_set_ref: ArtifactRef
    hook_candidate_set_ref: ArtifactRef
    allowed_strategy_ids: tuple[UUID, ...]
    allowed_hook_ids: tuple[UUID, ...]
    blocker_candidate_ids: tuple[UUID, ...] = ()
    candidate_brief_refs: tuple[ArtifactRef, ...]
    candidate_variant_plan_refs: tuple[ArtifactRef, ...]
    incomplete: bool = False

    @model_validator(mode="after")
    def require_unique_choices(self) -> Self:
        for values in (self.allowed_strategy_ids, self.allowed_hook_ids):
            if not values or len(values) != len(set(values)):
                raise ValueError("strategy review choices must be non-empty and unique")
        if not self.candidate_brief_refs or not self.candidate_variant_plan_refs:
            raise ValueError("strategy review requires Brief and Variant candidates")
        return self


class StrategyGateSelection(StrictContract):
    selected_strategy_id: UUID
    selected_hook_id: UUID
    creative_brief_ref: ArtifactRef
    variant_plan_ref: ArtifactRef
    accepted_risks: tuple[StableName, ...] = ()
    override_reason: Annotated[str, Field(min_length=1, max_length=4_096)] | None = None

    @model_validator(mode="after")
    def require_boundary_types(self) -> Self:
        if self.creative_brief_ref.artifact_type != "CreativeBrief":
            raise ValueError("strategy selection requires CreativeBrief ref")
        if self.variant_plan_ref.artifact_type != "VariantPlan":
            raise ValueError("strategy selection requires VariantPlan ref")
        return self


class ApprovedCreativeBrief(StrictContract):
    approved_story_ref: ArtifactRef
    effective_config_ref: ArtifactRef
    strategy_candidate_set_ref: ArtifactRef
    hook_candidate_set_ref: ArtifactRef
    selected_strategy_id: UUID
    selected_hook_id: UUID
    platform_profile_ref: ArtifactRef
    audience_profile_ref: ArtifactRef
    duration_profile_ref: ArtifactRef
    quality_profile_ref: ArtifactRef
    target_duration: RationalTime
    narrative_spine: tuple[NarrativeBeatIntent, ...]
    visual_intent: JsonObject
    rhythm_intent: JsonObject
    narration_intent: JsonObject
    audio_intent: JsonObject
    subtitle_intent: JsonObject
    hard_constraints: JsonObject
    soft_preferences: JsonObject
    must_use_story_refs: tuple[UUID, ...]
    must_avoid: tuple[Annotated[str, Field(min_length=1, max_length=2_048)], ...] = ()
    accepted_risks: tuple[StableName, ...] = ()
    cost_ceiling_micros: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def require_stage4_complete_boundary(self) -> Self:
        if not self.narrative_spine or not self.must_use_story_refs:
            raise ValueError("approved brief requires narrative spine and must-use Story refs")
        if self.target_duration.value <= 0:
            raise ValueError("approved brief target duration must be positive")
        return self


class VariantSpec(StrictContract):
    variant_id: UUID
    label: StableName
    control: bool
    changed_dimensions: dict[StableName, JsonObject | str | int | float | bool | None]
    estimated_incremental_cost_micros: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def require_experimental_change(self) -> Self:
        if self.control and self.changed_dimensions:
            raise ValueError("control variant cannot declare changed dimensions")
        if not self.control and not self.changed_dimensions:
            raise ValueError("candidate variant requires changed dimensions")
        return self


class VariantPlan(StrictContract):
    creative_brief_ref: ArtifactRef
    variants: tuple[VariantSpec, ...]
    budget_micros: Annotated[int, Field(ge=0)]
    candidate_variants_only: bool = True

    @model_validator(mode="after")
    def enforce_budget_and_control(self) -> Self:
        if not self.variants or sum(item.control for item in self.variants) != 1:
            raise ValueError("variant plan requires exactly one control")
        if (
            sum(item.estimated_incremental_cost_micros for item in self.variants)
            > self.budget_micros
        ):
            raise ValueError("variant plan exceeds budget")
        if not self.candidate_variants_only:
            raise ValueError("variants without exposure data cannot be called an experiment")
        return self
