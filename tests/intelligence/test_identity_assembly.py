from collections.abc import Iterator
from uuid import UUID, uuid4

from packages.contracts import ArtifactRef, IdentityEdge, IdentityNode
from packages.intelligence.identity import assemble_identity_graph, candidate_merge_pairs


def ref(kind: str = "VisualObservation") -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def evidence() -> dict[str, object]:
    return {
        "evidence_id": uuid4(),
        "source": ref(),
        "source_range": {
            "start": {"value": 0, "rate_num": 25},
            "duration": {"value": 25, "rate_num": 25},
        },
        "evidence_type": "visual",
        "excerpt": "face evidence",
    }


def confidence() -> dict[str, object]:
    return {
        "score": 0.95,
        "status": "shadow",
        "method": "test",
        "applicable_scope": "identity:test",
        "risk_class": "high",
    }


def node(name: str | None = None) -> IdentityNode:
    return IdentityNode.model_validate(
        {
            "node_id": uuid4(),
            "kind": "face_observation",
            "observation_ref": ref(),
            "source_ranges": [
                {
                    "start": {"value": 0, "rate_num": 25},
                    "duration": {"value": 25, "rate_num": 25},
                }
            ],
            "label_hint": name,
            "evidence": [evidence()],
        }
    )


def edge(
    left: IdentityNode, right: IdentityNode, relation: str, *, human: bool = False
) -> IdentityEdge:
    return IdentityEdge.model_validate(
        {
            "edge_id": uuid4(),
            "left_node_id": left.node_id,
            "right_node_id": right.node_id,
            "relation": relation,
            "evidence": [evidence()],
            "confidence": confidence(),
            "created_by_human": human,
        }
    )


def id_factory(values: Iterator[UUID]):
    return lambda: next(values)


def test_similarity_is_candidate_only_and_unknowns_remain_temporary() -> None:
    left, right = node(), node()
    candidate = edge(left, right, "same_candidate")
    graph = assemble_identity_graph(
        source_observation_refs=(ref(),), nodes=(left, right), edges=(candidate,)
    )
    assert len(graph.characters) == 2
    assert all(item.temporary for item in graph.characters)
    assert candidate_merge_pairs(graph) == ((left.node_id, right.node_id),)


def test_human_merge_is_replayable_with_injected_ids() -> None:
    left, right = node("阿明"), node("阿明")
    reviewed = edge(left, right, "corrected_same", human=True)
    character_id = uuid4()
    first = assemble_identity_graph(
        source_observation_refs=(ref(),),
        nodes=(right, left),
        edges=(reviewed,),
        character_id_factory=id_factory(iter((character_id,))),
    )
    assert len(first.characters) == 1
    assert first.characters[0].character_id == character_id
    assert first.characters[0].display_name == "阿明"
    assert first.characters[0].temporary is False


def test_cannot_link_overrides_same_and_creates_blocker() -> None:
    left, right = node(), node()
    same = edge(left, right, "corrected_same", human=True)
    different = edge(left, right, "corrected_different", human=True)
    graph = assemble_identity_graph(
        source_observation_refs=(ref(),), nodes=(left, right), edges=(same, different)
    )
    assert len(graph.characters) == 2
    assert graph.incomplete is True
    assert graph.conflicts[0].severity.value == "blocker"
    assert set(graph.conflicts[0].edge_ids) == {same.edge_id, different.edge_id}
    assert candidate_merge_pairs(graph) == ()
