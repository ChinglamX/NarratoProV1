from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import IdentityEdge, IdentityGraph, IdentityNode, IdentityProposal


def ref(kind: str = "VisualObservation") -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def time_range() -> dict[str, object]:
    return {"start": {"value": 0, "rate_num": 25}, "duration": {"value": 25, "rate_num": 25}}


def evidence() -> dict[str, object]:
    return {
        "evidence_id": uuid4(),
        "source": ref(),
        "source_range": time_range(),
        "evidence_type": "visual",
        "excerpt": "frontal face",
    }


def confidence() -> dict[str, object]:
    return {
        "score": 0.9,
        "status": "shadow",
        "method": "identity-link-v1",
        "applicable_scope": "identity:test",
        "risk_class": "high",
        "evidence": [evidence()],
    }


def node() -> IdentityNode:
    return IdentityNode.model_validate(
        {
            "node_id": uuid4(),
            "kind": "face_observation",
            "observation_ref": ref(),
            "source_ranges": [time_range()],
            "evidence": [evidence()],
        }
    )


def test_identity_contracts_round_trip_and_reject_ungrounded_nodes() -> None:
    item = node()
    graph = IdentityGraph(
        source_observation_refs=(item.observation_ref,),
        nodes=(item,),
        edges=(),
        characters=(),
        incomplete=True,
    )
    assert IdentityGraph.model_validate_json(graph.canonical_json()) == graph
    with pytest.raises(ValidationError, match="non-empty source ranges"):
        IdentityNode.model_validate(
            {
                "node_id": uuid4(),
                "kind": "face_observation",
                "observation_ref": ref(),
                "source_ranges": [],
                "evidence": [evidence()],
            }
        )


def test_human_corrections_and_proposals_fail_closed() -> None:
    left, right = node(), node()
    with pytest.raises(ValidationError, match="human source"):
        IdentityEdge.model_validate(
            {
                "edge_id": uuid4(),
                "left_node_id": left.node_id,
                "right_node_id": right.node_id,
                "relation": "corrected_same",
                "evidence": [evidence()],
                "confidence": confidence(),
            }
        )
    with pytest.raises(ValidationError, match="at least two characters"):
        IdentityProposal.model_validate(
            {
                "proposal_id": uuid4(),
                "base_graph_ref": ref("IdentityGraph"),
                "operation": "merge",
                "character_ids": [uuid4()],
                "node_ids": [],
                "reason": "candidate link",
                "evidence": [evidence()],
                "confidence": confidence(),
            }
        )
