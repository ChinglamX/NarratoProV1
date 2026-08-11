from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    EvidenceBundle,
    Fact,
    FactSet,
    SourceQualityFeature,
    SourceQualityFeatureSet,
    StoryGraph,
)


def ref(kind: str = "SourceMedia") -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def time_range() -> dict[str, object]:
    return {
        "start": {"value": 0, "rate_num": 25},
        "duration": {"value": 25, "rate_num": 25},
    }


def evidence() -> dict[str, object]:
    return {
        "evidence_id": uuid4(),
        "source": ref(),
        "source_range": time_range(),
        "evidence_type": "dialogue",
        "excerpt": "你终于回来了",
    }


def confidence() -> dict[str, object]:
    return {
        "score": 0.8,
        "status": "shadow",
        "method": "cross-modal",
        "applicable_scope": "story:v1",
        "risk_class": "medium",
    }


def fact(**overrides: object) -> Fact:
    values: dict[str, object] = {
        "fact_id": uuid4(),
        "fact_type": "dialogue",
        "value": {"text": "你终于回来了"},
        "source_range": time_range(),
        "evidence": [evidence()],
        "provider": {
            "provider": "local",
            "implementation": "asr",
            "version": "1",
            "license": "apache-2",
        },
        "confidence": confidence(),
        "status": "observed",
    }
    values.update(overrides)
    return Fact.model_validate(values)


def test_fact_and_evidence_contracts_preserve_grounding() -> None:
    item = fact()
    assert Fact.model_validate_json(item.canonical_json()) == item
    with pytest.raises(ValidationError, match="evidence"):
        fact(evidence=[])
    fact_set = FactSet(source_refs=(item.evidence[0].source,), facts=(item,))
    assert FactSet.model_validate_json(fact_set.canonical_json()) == fact_set
    bundle = EvidenceBundle(target_ref=ref("FactSet"), links=item.evidence)
    assert len(bundle.links) == 1


def test_fact_set_and_quality_feature_fail_closed() -> None:
    item = fact()
    with pytest.raises(ValidationError, match="unique"):
        FactSet(source_refs=(), facts=(item, item))
    with pytest.raises(ValidationError, match="incomplete"):
        FactSet(source_refs=(), facts=(), unavailable_partitions=("ocr",))
    with pytest.raises(ValidationError, match="requires a value"):
        SourceQualityFeature.model_validate(
            {
                "feature_id": uuid4(),
                "source": ref(),
                "source_range": time_range(),
                "metric": "blur",
                "method": "laplacian",
                "profile_ref": ref("ConfigArtifact"),
                "status": "measured",
            }
        )
    feature = SourceQualityFeature.model_validate(
        {
            "feature_id": uuid4(),
            "source": ref(),
            "source_range": time_range(),
            "metric": "blur",
            "method": "laplacian",
            "profile_ref": ref("ConfigArtifact"),
            "status": "measured",
            "value": 42,
            "unit": "variance",
        }
    )
    feature_set = SourceQualityFeatureSet(source=feature.source, features=(feature,))
    assert SourceQualityFeatureSet.model_validate_json(feature_set.canonical_json()) == feature_set


def character(character_id=None) -> dict[str, object]:
    return {
        "character_id": character_id or uuid4(),
        "display_name": "阿明",
        "evidence": [evidence()],
    }


def event(event_id=None, participants=()) -> dict[str, object]:
    return {
        "event_id": event_id or uuid4(),
        "order_key": "episode-1:001",
        "description": "阿明回到村里",
        "participants": participants,
        "evidence": [evidence()],
        "confidence": confidence(),
        "importance": "key",
    }


def test_story_graph_validates_grounding_and_references() -> None:
    character_id = uuid4()
    event_id = uuid4()
    graph = StoryGraph.model_validate(
        {
            "source_fact_refs": [ref("FactSet")],
            "characters": [
                {
                    **character(character_id),
                    "identity_links": [
                        {
                            "identity_ref": "identity-cluster-1",
                            "relation": "matches",
                            "evidence": [evidence()],
                        }
                    ],
                }
            ],
            "events": [event(event_id, (character_id,))],
            "edges": [
                {
                    "edge_id": uuid4(),
                    "edge_type": "changes_state",
                    "from_ref": character_id,
                    "to_ref": event_id,
                    "evidence": [evidence()],
                    "confidence": confidence(),
                }
            ],
            "arcs": [
                {
                    "arc_id": uuid4(),
                    "arc_type": "return",
                    "description": "返乡线",
                    "event_refs": [event_id],
                    "protagonist_refs": [character_id],
                    "evidence": [evidence()],
                }
            ],
            "unresolved_questions": [
                {
                    "question_id": uuid4(),
                    "question": "阿明为何返乡?",
                    "related_refs": [event_id],
                    "evidence": [evidence()],
                }
            ],
        }
    )
    assert StoryGraph.model_validate_json(graph.canonical_json()) == graph
    with pytest.raises(ValidationError, match="unknown character"):
        StoryGraph.model_validate(
            {
                "source_fact_refs": [],
                "characters": [character(character_id)],
                "events": [event(event_id, (uuid4(),))],
                "edges": [],
            }
        )
    with pytest.raises(ValidationError, match="key event requires evidence"):
        StoryGraph.model_validate(
            {
                "source_fact_refs": [],
                "characters": [character(character_id)],
                "events": [{**event(event_id, (character_id,)), "evidence": []}],
                "edges": [],
            }
        )
