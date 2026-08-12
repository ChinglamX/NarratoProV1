from uuid import uuid4

from packages.contracts import (
    ArtifactRef,
    CharacterIdentity,
    Fact,
    FactSet,
    IdentityGraph,
    IdentityNode,
)
from packages.intelligence.story import (
    assemble_story_graph,
    build_event_set,
    retrieve_story_facts,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate({"artifact_id": uuid4(), "version": 1, "artifact_type": kind})


def evidence() -> dict[str, object]:
    return {
        "evidence_id": uuid4(),
        "source": ref("SpeechObservation"),
        "source_range": {
            "start": {"value": 0, "rate_num": 25},
            "duration": {"value": 25, "rate_num": 25},
        },
        "evidence_type": "dialogue",
        "excerpt": "我回来了",
    }


def confidence() -> dict[str, object]:
    return {
        "score": 0.8,
        "status": "shadow",
        "method": "test",
        "applicable_scope": "story:test",
        "risk_class": "high",
    }


def fact(kind: str, status: str = "observed") -> Fact:
    return Fact.model_validate(
        {
            "fact_id": uuid4(),
            "fact_type": kind,
            "value": {"text": "我回来了"},
            "source_range": {
                "start": {"value": 0, "rate_num": 25},
                "duration": {"value": 25, "rate_num": 25},
            },
            "evidence": [evidence()],
            "provider": {
                "provider": "fixture",
                "implementation": "fixture",
                "version": "1",
                "license": "test-only",
            },
            "confidence": confidence(),
            "status": status,
        }
    )


def identity() -> IdentityGraph:
    node = IdentityNode.model_validate(
        {
            "node_id": uuid4(),
            "kind": "speaker_cluster",
            "observation_ref": ref("SpeechObservation"),
            "source_ranges": [
                {
                    "start": {"value": 0, "rate_num": 25},
                    "duration": {"value": 25, "rate_num": 25},
                }
            ],
            "evidence": [evidence()],
        }
    )
    character = CharacterIdentity(
        character_id=uuid4(),
        member_node_ids=(node.node_id,),
        temporary=True,
        evidence=node.evidence,
    )
    return IdentityGraph(
        source_observation_refs=(node.observation_ref,),
        nodes=(node,),
        edges=(),
        characters=(character,),
    )


def test_story_stages_do_not_turn_time_order_into_causality() -> None:
    fact_ref = ref("FactSet")
    facts = FactSet(
        source_refs=(ref("SpeechObservation"),),
        facts=(fact("dialogue"), fact("ocr"), fact("action")),
    )
    selected = retrieve_story_facts(facts)
    events = build_event_set(fact_ref=fact_ref, facts=selected)
    story = assemble_story_graph(fact_ref=fact_ref, identity=identity(), event_set=events)
    assert len(events.events) == 2
    assert story.edges == ()
    assert story.characters[0].temporary and story.characters[0].display_name is None


def test_disputed_fact_is_not_automatically_promoted() -> None:
    facts = FactSet(source_refs=(), facts=(fact("dialogue", "disputed"),))
    assert retrieve_story_facts(facts) == ()
