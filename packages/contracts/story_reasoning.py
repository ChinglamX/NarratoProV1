"""Typed intermediate artifacts for staged Story reasoning."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.evidence import ConfidenceRecord, EvidenceLink
from packages.contracts.foundation import UUID, ArtifactRef, StableName, TimeRange
from packages.contracts.story import Event, StoryEdge


class EntailmentStatus(StrEnum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"


class EventCandidate(StrictContract):
    candidate_id: UUID
    source_fact_ids: tuple[UUID, ...]
    description: Annotated[str, Field(min_length=1, max_length=8_192)]
    source_range: TimeRange
    participant_refs: tuple[UUID, ...] = ()
    evidence: tuple[EvidenceLink, ...]
    confidence: ConfidenceRecord
    entailment: EntailmentStatus

    @model_validator(mode="after")
    def require_sources(self) -> Self:
        if not self.source_fact_ids or not self.evidence or self.source_range.is_empty:
            raise ValueError("event candidate requires fact, evidence and non-empty range")
        return self


class EventSet(StrictContract):
    source_fact_ref: ArtifactRef
    candidates: tuple[EventCandidate, ...]
    events: tuple[Event, ...]
    unresolved_candidate_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def validate_resolution(self) -> Self:
        candidate_ids = {item.candidate_id for item in self.candidates}
        if not set(self.unresolved_candidate_ids) <= candidate_ids:
            raise ValueError("unresolved event candidate is unknown")
        return self


class CharacterState(StrictContract):
    state_id: UUID
    character_id: UUID
    state_type: StableName
    value: Annotated[str, Field(min_length=1, max_length=4_096)]
    valid_range: TimeRange
    evidence: tuple[EvidenceLink, ...]
    confidence: ConfidenceRecord


class CharacterStateGraph(StrictContract):
    source_event_ref: ArtifactRef
    states: tuple[CharacterState, ...]
    unresolved_character_ids: tuple[UUID, ...] = ()


class CausalGraph(StrictContract):
    source_event_ref: ArtifactRef
    edges: tuple[StoryEdge, ...]
    unresolved_pairs: tuple[tuple[UUID, UUID], ...] = ()

    @model_validator(mode="after")
    def keep_unresolved_pairs_distinct(self) -> Self:
        if any(left == right for left, right in self.unresolved_pairs):
            raise ValueError("unresolved causal pair cannot be a self pair")
        return self


class StoryReasoningReport(StrictContract):
    fact_ref: ArtifactRef
    identity_ref: ArtifactRef
    event_set_ref: ArtifactRef
    character_state_ref: ArtifactRef
    causal_graph_ref: ArtifactRef
    story_graph_ref: ArtifactRef
    contradiction_count: Annotated[int, Field(ge=0)]
    unresolved_count: Annotated[int, Field(ge=0)]
    incomplete: bool


class StoryReviewPackage(StrictContract):
    fact_ref: ArtifactRef
    identity_ref: ArtifactRef
    event_set_ref: ArtifactRef
    character_state_ref: ArtifactRef
    causal_graph_ref: ArtifactRef
    story_graph_ref: ArtifactRef
    config_refs: tuple[ArtifactRef, ...]
    model_refs: tuple[ArtifactRef, ...] = ()
    blocker_codes: tuple[StableName, ...] = ()
    unresolved_count: Annotated[int, Field(ge=0)] = 0
    incomplete: bool = False

    @model_validator(mode="after")
    def require_exact_types_and_config(self) -> Self:
        expected = {
            "fact_ref": "FactSet",
            "identity_ref": "IdentityGraph",
            "event_set_ref": "EventSet",
            "character_state_ref": "CharacterStateGraph",
            "causal_graph_ref": "CausalGraph",
            "story_graph_ref": "StoryGraph",
        }
        for field_name, artifact_type in expected.items():
            if getattr(self, field_name).artifact_type != artifact_type:
                raise ValueError(f"{field_name} must reference {artifact_type}")
        if not self.config_refs:
            raise ValueError("story review package requires exact config refs")
        return self


class ApprovedStorySnapshot(StrictContract):
    review_id: UUID
    decision_id: UUID
    story_ref: ArtifactRef
    fact_ref: ArtifactRef
    identity_ref: ArtifactRef
    event_set_ref: ArtifactRef
    character_state_ref: ArtifactRef
    causal_graph_ref: ArtifactRef
    config_refs: tuple[ArtifactRef, ...]
    model_refs: tuple[ArtifactRef, ...] = ()
