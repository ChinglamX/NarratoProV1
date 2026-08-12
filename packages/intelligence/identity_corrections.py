"""Human-only semantic identity corrections and deterministic impact previews."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

from packages.contracts.foundation import ArtifactRef
from packages.contracts.identity import (
    CharacterIdentity,
    IdentityCorrectionResult,
    IdentityEdge,
    IdentityGraph,
    IdentityProposal,
    IdentityProposalOperation,
    IdentityRelation,
)


class IdentityCorrectionConflict(RuntimeError):
    pass


def _edge(
    left: UUID,
    right: UUID,
    proposal: IdentityProposal,
    relation: IdentityRelation,
    edge_id_factory: Callable[[], UUID],
) -> IdentityEdge:
    return IdentityEdge(
        edge_id=edge_id_factory(),
        left_node_id=left,
        right_node_id=right,
        relation=relation,
        evidence=proposal.evidence,
        confidence=proposal.confidence,
        created_by_human=True,
    )


def apply_identity_proposal(
    graph: IdentityGraph,
    proposal: IdentityProposal,
    *,
    new_character_id_factory: Callable[[], UUID] = uuid4,
    edge_id_factory: Callable[[], UUID] = uuid4,
) -> tuple[IdentityGraph, tuple[UUID, ...]]:
    """Return an immutable successor candidate; persistence and CAS remain adapter concerns."""

    if proposal.proposal_id in graph.applied_proposal_ids:
        raise IdentityCorrectionConflict("identity proposal was already applied")
    by_id = {item.character_id: item for item in graph.characters}
    if not set(proposal.character_ids) <= set(by_id):
        raise IdentityCorrectionConflict("proposal references unknown character")
    characters = list(graph.characters)
    edges = list(graph.edges)
    changed: set[UUID] = set(proposal.character_ids)

    if proposal.operation is IdentityProposalOperation.MERGE:
        selected = [by_id[item] for item in proposal.character_ids]
        anchor = selected[0]
        members = tuple(
            sorted({node for item in selected for node in item.member_node_ids}, key=str)
        )
        evidence = tuple(link for item in selected for link in item.evidence)
        names = sorted({item.display_name for item in selected if item.display_name})
        display_name = names[0] if len(names) == 1 else None
        merged = CharacterIdentity(
            character_id=anchor.character_id,
            display_name=display_name,
            aliases=tuple(name for name in names[1:] if display_name),
            member_node_ids=members,
            temporary=display_name is None,
            evidence=evidence,
        )
        removed = set(proposal.character_ids)
        characters = [item for item in characters if item.character_id not in removed]
        characters.append(merged)
        for item in selected[1:]:
            edges.append(
                _edge(
                    anchor.member_node_ids[0],
                    item.member_node_ids[0],
                    proposal,
                    IdentityRelation.CORRECTED_SAME,
                    edge_id_factory,
                )
            )
    elif proposal.operation is IdentityProposalOperation.SPLIT:
        if len(proposal.character_ids) != 1:
            raise IdentityCorrectionConflict("split requires exactly one character")
        source = by_id[proposal.character_ids[0]]
        split_nodes = set(proposal.node_ids)
        if not split_nodes or not split_nodes < set(source.member_node_ids):
            raise IdentityCorrectionConflict("split must select a proper non-empty member subset")
        remaining = tuple(item for item in source.member_node_ids if item not in split_nodes)
        separated = tuple(sorted(split_nodes, key=str))
        retained = source.model_copy(update={"member_node_ids": remaining})
        created_id = new_character_id_factory()
        created = CharacterIdentity(
            character_id=created_id,
            member_node_ids=separated,
            temporary=True,
            evidence=proposal.evidence,
        )
        characters = [item for item in characters if item.character_id != source.character_id]
        characters.extend((retained, created))
        changed.add(created_id)
        for left in remaining:
            for right in separated:
                edges.append(
                    _edge(
                        left,
                        right,
                        proposal,
                        IdentityRelation.CORRECTED_DIFFERENT,
                        edge_id_factory,
                    )
                )
    elif proposal.operation in {
        IdentityProposalOperation.ASSIGN_NAME,
        IdentityProposalOperation.UNASSIGN_NAME,
    }:
        if len(proposal.character_ids) != 1:
            raise IdentityCorrectionConflict("name correction requires exactly one character")
        target_id = proposal.character_ids[0]
        target = by_id[target_id]
        name = proposal.proposed_name
        updated = target.model_copy(update={"display_name": name, "temporary": name is None})
        characters = [updated if item.character_id == target_id else item for item in characters]
    else:  # pragma: no cover - enum exhaustiveness guard
        raise IdentityCorrectionConflict("unsupported identity proposal")

    successor = graph.model_copy(
        update={
            "edges": tuple(edges),
            "characters": tuple(sorted(characters, key=lambda item: str(item.character_id))),
            "applied_proposal_ids": (*graph.applied_proposal_ids, proposal.proposal_id),
        }
    )
    return IdentityGraph.model_validate(successor), tuple(sorted(changed, key=str))


def preview_identity_correction(
    *,
    graph_ref: ArtifactRef,
    graph: IdentityGraph,
    proposal: IdentityProposal,
    downstream_refs: tuple[ArtifactRef, ...] = (),
    new_character_id_factory: Callable[[], UUID] = uuid4,
    edge_id_factory: Callable[[], UUID] = uuid4,
) -> IdentityCorrectionResult:
    if proposal.base_graph_ref != graph_ref:
        raise IdentityCorrectionConflict("proposal base graph is stale or mismatched")
    result, changed = apply_identity_proposal(
        graph,
        proposal,
        new_character_id_factory=new_character_id_factory,
        edge_id_factory=edge_id_factory,
    )
    return IdentityCorrectionResult(
        before_ref=graph_ref,
        proposal=proposal,
        resulting_graph=result,
        affected_refs=downstream_refs,
        changed_character_ids=changed,
    )
