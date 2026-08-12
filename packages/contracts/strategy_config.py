"""Versioned Stage 3 profiles and deterministic effective strategy configuration."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, JsonValue, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import UUID, ArtifactRef, StableName


class ProfileStatus(StrEnum):
    DRAFT = "draft"
    EXPERIMENTAL = "experimental"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class StrategyProfileKind(StrEnum):
    GENRE = "genre"
    PLATFORM = "platform"
    AUDIENCE = "audience"
    DURATION = "duration"
    BRAND_SAFETY = "brand_safety"


class StrategyProfile(StrictContract):
    profile_id: UUID
    profile_version: Annotated[str, Field(min_length=1, max_length=128)]
    schema_version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    kind: StrategyProfileKind
    name: StableName
    applicable_scope: tuple[StableName, ...]
    validated_scope: tuple[StableName, ...] = ()
    source: Annotated[str, Field(min_length=1, max_length=2_048)]
    owner: StableName
    status: ProfileStatus
    hard_constraints: dict[StableName, JsonValue] = Field(default_factory=dict)
    soft_preferences: dict[StableName, JsonValue] = Field(default_factory=dict)
    known_limitations: tuple[Annotated[str, Field(min_length=1, max_length=2_048)], ...] = ()

    @model_validator(mode="after")
    def enforce_profile_semantics(self) -> Self:
        if not self.applicable_scope:
            raise ValueError("strategy profile requires applicable scope")
        if (
            self.kind
            in {
                StrategyProfileKind.GENRE,
                StrategyProfileKind.AUDIENCE,
                StrategyProfileKind.DURATION,
            }
            and self.hard_constraints
        ):
            raise ValueError("genre/audience/duration profiles cannot create hard constraints")
        if self.status is ProfileStatus.APPROVED and not self.validated_scope:
            raise ValueError("approved profile requires validated scope")
        return self


class ConstraintSource(StrEnum):
    RIGHTS_SAFETY = "rights_safety"
    PLATFORM = "platform"
    PROJECT_BRIEF = "project_brief"
    HUMAN_OVERRIDE = "human_override"


class ResolvedStrategyValue(StrictContract):
    key: StableName
    value: JsonValue
    hard: bool
    source: ConstraintSource | StableName
    source_ref: ArtifactRef
    overridden_source_refs: tuple[ArtifactRef, ...] = ()


class StrategyConfigConflict(StrictContract):
    key: StableName
    source_refs: tuple[ArtifactRef, ...]
    detail: Annotated[str, Field(min_length=1, max_length=2_048)]
    blocker: bool = True


class EffectiveStrategyConfig(StrictContract):
    approved_story_ref: ArtifactRef
    project_brief_ref: ArtifactRef
    profile_refs: tuple[ArtifactRef, ...]
    values: tuple[ResolvedStrategyValue, ...]
    conflicts: tuple[StrategyConfigConflict, ...] = ()

    @model_validator(mode="after")
    def require_approved_story_and_unique_keys(self) -> Self:
        if self.approved_story_ref.artifact_type != "StoryGraph":
            raise ValueError("strategy config requires approved StoryGraph ref")
        keys = [item.key for item in self.values]
        if len(keys) != len(set(keys)):
            raise ValueError("effective strategy config keys must be unique")
        return self

    @property
    def blocked(self) -> bool:
        return any(item.blocker for item in self.conflicts)


class GenreCandidate(StrictContract):
    genre: StableName
    story_refs: tuple[UUID, ...]
    evidence_summary: Annotated[str, Field(min_length=1, max_length=4_096)]
    config_ref: ArtifactRef | None = None
    primary: bool = False
    experimental: bool = True


class GenreResolution(StrictContract):
    approved_story_ref: ArtifactRef
    candidates: tuple[GenreCandidate, ...]
    human_override: StableName | None = None

    @model_validator(mode="after")
    def preserve_multiple_or_unknown(self) -> Self:
        if not self.candidates:
            raise ValueError("genre resolution requires candidates, including unknown")
        if sum(item.primary for item in self.candidates) > 1:
            raise ValueError("genre resolution supports at most one primary candidate")
        return self
