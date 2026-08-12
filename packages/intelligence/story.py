"""Deterministic typed Story stages; no direct video-to-story shortcut."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import UUID, uuid4

from packages.contracts import (
    ArtifactRef,
    Character,
    Event,
    Fact,
    FactSet,
    IdentityGraph,
    StoryGraph,
    StoryImportance,
)
from packages.contracts.story_reasoning import EntailmentStatus, EventCandidate, EventSet


def retrieve_story_facts(fact_set: FactSet) -> tuple[Fact, ...]:
    """Keep observed/corrected facts; disputed facts remain outside automatic event creation."""

    return tuple(
        sorted(
            (item for item in fact_set.facts if item.status.value in {"observed", "corrected"}),
            key=lambda item: (item.source_range.start.seconds, str(item.fact_id)),
        )
    )


def build_event_set(
    *,
    fact_ref: ArtifactRef,
    facts: Sequence[Fact],
    participant_by_subject: dict[str, UUID] | None = None,
    id_factory: Callable[[], UUID] = uuid4,
) -> EventSet:
    """Create candidates only for fact types with event semantics; never invent causality."""

    participants = participant_by_subject or {}
    candidates: list[EventCandidate] = []
    events: list[Event] = []
    unresolved: list[UUID] = []
    for index, fact in enumerate(facts):
        if fact.fact_type.value not in {"dialogue", "action", "audio_signal", "visual_signal"}:
            continue
        description = str(fact.value)
        candidate_id = id_factory()
        participant = participants.get(str(fact.subject_ref)) if fact.subject_ref else None
        candidate = EventCandidate(
            candidate_id=candidate_id,
            source_fact_ids=(fact.fact_id,),
            description=description,
            source_range=fact.source_range,
            participant_refs=(participant,) if participant else (),
            evidence=fact.evidence,
            confidence=fact.confidence,
            entailment=EntailmentStatus.SUPPORTED,
        )
        candidates.append(candidate)
        event = Event(
            event_id=id_factory(),
            order_key=f"event:{index:08d}",
            description=description,
            participants=candidate.participant_refs,
            source_range=fact.source_range,
            evidence=fact.evidence,
            confidence=fact.confidence,
            importance=StoryImportance.SUPPORTING,
        )
        events.append(event)
    return EventSet(
        source_fact_ref=fact_ref,
        candidates=tuple(candidates),
        events=tuple(events),
        unresolved_candidate_ids=tuple(unresolved),
    )


def story_characters(identity: IdentityGraph) -> tuple[Character, ...]:
    nodes = {node.node_id: node for node in identity.nodes}
    result = []
    for item in identity.characters:
        evidence = tuple(
            link for node_id in item.member_node_ids for link in nodes[node_id].evidence
        )
        result.append(
            Character(
                character_id=item.character_id,
                display_name=item.display_name,
                temporary=item.temporary,
                aliases=item.aliases,
                evidence=evidence,
            )
        )
    return tuple(result)


def assemble_story_graph(
    *, fact_ref: ArtifactRef, identity: IdentityGraph, event_set: EventSet
) -> StoryGraph:
    """Assemble evidence-grounded nodes; temporal order never becomes a causal edge."""

    return StoryGraph(
        source_fact_refs=(fact_ref,),
        characters=story_characters(identity),
        events=event_set.events,
        edges=(),
        unresolved_questions=(),
    )
