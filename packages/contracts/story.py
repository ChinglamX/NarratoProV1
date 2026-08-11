"""Canonical evidence-grounded story intelligence contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.evidence import ConfidenceRecord, EvidenceLink
from packages.contracts.foundation import UUID, ArtifactRef, StableName, TimeRange

Text = Annotated[str, Field(min_length=1, max_length=8_192)]


class IdentityLink(StrictContract):
    identity_ref: StableName
    relation: StableName
    evidence: tuple[EvidenceLink, ...]


class Character(StrictContract):
    character_id: UUID
    display_name: Annotated[str, Field(min_length=1, max_length=512)]
    aliases: tuple[Annotated[str, Field(min_length=1, max_length=512)], ...] = ()
    identity_links: tuple[IdentityLink, ...] = ()
    evidence: tuple[EvidenceLink, ...]

    @model_validator(mode="after")
    def require_identity_evidence(self) -> Self:
        if not self.evidence:
            raise ValueError("character requires evidence")
        return self


class StoryImportance(StrEnum):
    KEY = "key"
    SUPPORTING = "supporting"
    CONTEXT = "context"


class Event(StrictContract):
    event_id: UUID
    order_key: StableName
    description: Text
    participants: tuple[UUID, ...]
    source_range: TimeRange | None = None
    evidence: tuple[EvidenceLink, ...]
    confidence: ConfidenceRecord
    importance: StoryImportance

    @model_validator(mode="after")
    def require_key_event_grounding(self) -> Self:
        if self.importance is StoryImportance.KEY and not self.evidence:
            raise ValueError("key event requires evidence")
        if len(set(self.participants)) != len(self.participants):
            raise ValueError("event participants must be unique")
        return self


class StoryEdgeType(StrEnum):
    CAUSES = "causes"
    ENABLES = "enables"
    REVEALS = "reveals"
    CONTRADICTS = "contradicts"
    CHANGES_RELATIONSHIP = "changes_relationship"
    CHANGES_STATE = "changes_state"


class StoryEdge(StrictContract):
    edge_id: UUID
    edge_type: StoryEdgeType
    from_ref: UUID
    to_ref: UUID
    evidence: tuple[EvidenceLink, ...]
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def reject_self_edge_and_ungrounded_claim(self) -> Self:
        if self.from_ref == self.to_ref:
            raise ValueError("story edge cannot point to itself")
        if not self.evidence:
            raise ValueError("story edge requires evidence")
        return self


class StoryArc(StrictContract):
    arc_id: UUID
    arc_type: StableName
    description: Text
    event_refs: tuple[UUID, ...]
    protagonist_refs: tuple[UUID, ...] = ()
    evidence: tuple[EvidenceLink, ...]


class UnresolvedQuestion(StrictContract):
    question_id: UUID
    question: Text
    related_refs: tuple[UUID, ...]
    evidence: tuple[EvidenceLink, ...] = ()


class StoryGraph(StrictContract):
    source_fact_refs: tuple[ArtifactRef, ...]
    characters: tuple[Character, ...]
    events: tuple[Event, ...]
    edges: tuple[StoryEdge, ...]
    arcs: tuple[StoryArc, ...] = ()
    unresolved_questions: tuple[UnresolvedQuestion, ...] = ()

    @model_validator(mode="after")
    def validate_graph_references(self) -> Self:
        character_ids = {item.character_id for item in self.characters}
        event_ids = {item.event_id for item in self.events}
        if len(character_ids) != len(self.characters) or len(event_ids) != len(self.events):
            raise ValueError("character and event ids must be unique")
        if any(not set(item.participants) <= character_ids for item in self.events):
            raise ValueError("event references unknown character")
        graph_ids = character_ids | event_ids
        if any(
            item.from_ref not in graph_ids or item.to_ref not in graph_ids for item in self.edges
        ):
            raise ValueError("story edge references unknown graph node")
        if any(not set(item.event_refs) <= event_ids for item in self.arcs):
            raise ValueError("story arc references unknown event")
        if any(not set(item.protagonist_refs) <= character_ids for item in self.arcs):
            raise ValueError("story arc references unknown protagonist")
        return self
