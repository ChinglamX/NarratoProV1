from uuid import uuid4

import pytest

from packages.contracts import (
    ArtifactRef,
    CharacterIdentity,
    IdentityGraph,
    IdentityNode,
    IdentityProposal,
)
from packages.intelligence.identity_corrections import (
    IdentityCorrectionConflict,
    preview_identity_correction,
)


def ref(kind: str = "IdentityGraph", *, artifact_id=None, version: int = 1) -> ArtifactRef:
    return ArtifactRef(artifact_id=artifact_id or uuid4(), version=version, artifact_type=kind)


def evidence() -> dict[str, object]:
    return {
        "evidence_id": uuid4(),
        "source": ref("VisualObservation"),
        "source_range": {
            "start": {"value": 0, "rate_num": 25},
            "duration": {"value": 25, "rate_num": 25},
        },
        "evidence_type": "human_note",
        "excerpt": "reviewed identity evidence",
    }


def confidence() -> dict[str, object]:
    return {
        "score": 1.0,
        "status": "shadow",
        "method": "human-review",
        "applicable_scope": "identity:test",
        "risk_class": "high",
    }


def graph() -> IdentityGraph:
    nodes = tuple(
        IdentityNode.model_validate(
            {
                "node_id": uuid4(),
                "kind": "face_observation",
                "observation_ref": ref("VisualObservation"),
                "source_ranges": [
                    {
                        "start": {"value": index, "rate_num": 1},
                        "duration": {"value": 1, "rate_num": 1},
                    }
                ],
                "evidence": [evidence()],
            }
        )
        for index in range(3)
    )
    characters = tuple(
        CharacterIdentity(
            character_id=uuid4(),
            member_node_ids=(item.node_id,),
            temporary=True,
            evidence=item.evidence,
        )
        for item in nodes
    )
    return IdentityGraph(
        source_observation_refs=(ref("VisualObservation"),),
        nodes=nodes,
        edges=(),
        characters=characters,
    )


def proposal(base: ArtifactRef, operation: str, characters=(), nodes=(), name=None):
    return IdentityProposal.model_validate(
        {
            "proposal_id": uuid4(),
            "base_graph_ref": base,
            "operation": operation,
            "character_ids": characters,
            "node_ids": nodes,
            "proposed_name": name,
            "reason": "reviewer correction",
            "evidence": [evidence()],
            "confidence": confidence(),
        }
    )


def test_merge_split_and_name_corrections_are_successors() -> None:
    value = graph()
    base = ref()
    merge = proposal(
        base,
        "merge",
        tuple(item.character_id for item in value.characters[:2]),
    )
    merged = preview_identity_correction(graph_ref=base, graph=value, proposal=merge)
    assert len(merged.resulting_graph.characters) == 2
    assert merged.resulting_graph.edges[-1].created_by_human
    merged_character = next(
        item for item in merged.resulting_graph.characters if len(item.member_node_ids) == 2
    )
    next_ref = ref(artifact_id=base.artifact_id, version=2)
    split = proposal(
        next_ref,
        "split",
        (merged_character.character_id,),
        (merged_character.member_node_ids[-1],),
    )
    split_result = preview_identity_correction(
        graph_ref=next_ref,
        graph=merged.resulting_graph,
        proposal=split,
        new_character_id_factory=lambda: uuid4(),
    )
    assert len(split_result.resulting_graph.characters) == 3
    assert len(split_result.resulting_graph.applied_proposal_ids) == 2
    assert split_result.resulting_graph.edges[-1].relation.value == "corrected_different"


def test_stale_duplicate_and_invalid_split_fail_closed() -> None:
    value = graph()
    base = ref()
    item = proposal(base, "assign_name", (value.characters[0].character_id,), name="阿明")
    first = preview_identity_correction(graph_ref=base, graph=value, proposal=item)
    named = next(
        character
        for character in first.resulting_graph.characters
        if character.character_id == value.characters[0].character_id
    )
    assert named.display_name == "阿明" and not named.temporary
    with pytest.raises(IdentityCorrectionConflict, match="already applied"):
        preview_identity_correction(graph_ref=base, graph=first.resulting_graph, proposal=item)
    stale = item.model_copy(update={"base_graph_ref": ref()})
    with pytest.raises(IdentityCorrectionConflict, match="stale"):
        preview_identity_correction(graph_ref=base, graph=value, proposal=stale)
