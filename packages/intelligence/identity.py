"""Deterministic conservative identity assembly from reviewed hard constraints."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from uuid import UUID, uuid4

from packages.contracts.foundation import ArtifactRef
from packages.contracts.identity import (
    CharacterIdentity,
    IdentityConflict,
    IdentityConflictSeverity,
    IdentityEdge,
    IdentityGraph,
    IdentityNode,
    IdentityRelation,
)


class _UnionFind:
    def __init__(self, nodes: Sequence[UUID]) -> None:
        self.parent = {node: node for node in nodes}

    def find(self, node: UUID) -> UUID:
        root = node
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[node] != node:
            node, self.parent[node] = self.parent[node], root
        return root

    def union(self, left: UUID, right: UUID) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            smaller, larger = sorted((left_root, right_root), key=str)
            self.parent[larger] = smaller


def assemble_identity_graph(
    *,
    source_observation_refs: Sequence[ArtifactRef],
    nodes: Sequence[IdentityNode],
    edges: Sequence[IdentityEdge],
    incomplete: bool = False,
    character_id_factory: Callable[[], UUID] = uuid4,
    conflict_id_factory: Callable[[], UUID] = uuid4,
) -> IdentityGraph:
    """Apply only human corrections as merge authority; candidates remain review evidence."""

    known = {node.node_id: node for node in nodes}
    if any(edge.left_node_id not in known or edge.right_node_id not in known for edge in edges):
        raise ValueError("identity edge references unknown node")
    cannot_edges: dict[frozenset[UUID], list[IdentityEdge]] = defaultdict(list)
    for item in edges:
        if item.relation in {IdentityRelation.CANNOT_BE_SAME, IdentityRelation.CORRECTED_DIFFERENT}:
            cannot_edges[frozenset((item.left_node_id, item.right_node_id))].append(item)
    union = _UnionFind(tuple(known))
    conflicts: list[IdentityConflict] = []
    for edge in sorted(edges, key=lambda item: str(item.edge_id)):
        if edge.relation is not IdentityRelation.CORRECTED_SAME:
            continue
        pair = frozenset((edge.left_node_id, edge.right_node_id))
        if pair in cannot_edges:
            constraints = sorted(cannot_edges[pair], key=lambda item: str(item.edge_id))
            conflicts.append(
                IdentityConflict(
                    conflict_id=conflict_id_factory(),
                    conflict_type="human-same-vs-cannot-link",
                    severity=IdentityConflictSeverity.BLOCKER,
                    node_ids=(edge.left_node_id, edge.right_node_id),
                    edge_ids=(edge.edge_id, *(item.edge_id for item in constraints)),
                    detail="A reviewed same-person edge conflicts with a cannot-link constraint",
                    evidence=edge.evidence,
                )
            )
            continue
        union.union(edge.left_node_id, edge.right_node_id)
    components: dict[UUID, list[IdentityNode]] = defaultdict(list)
    for node in nodes:
        components[union.find(node.node_id)].append(node)
    characters = []

    def component_order(items: list[IdentityNode]) -> str:
        return min(str(item.node_id) for item in items)

    for component in sorted(components.values(), key=component_order):
        ordered = sorted(component, key=lambda item: str(item.node_id))
        name_hints = sorted({item.label_hint for item in ordered if item.label_hint})
        display_name = name_hints[0] if len(name_hints) == 1 else None
        characters.append(
            CharacterIdentity(
                character_id=character_id_factory(),
                display_name=display_name,
                aliases=tuple(name_hints[1:]) if display_name else (),
                member_node_ids=tuple(item.node_id for item in ordered),
                temporary=display_name is None,
                evidence=tuple(link for item in ordered for link in item.evidence),
            )
        )
    return IdentityGraph(
        source_observation_refs=tuple(source_observation_refs),
        nodes=tuple(nodes),
        edges=tuple(edges),
        characters=tuple(characters),
        conflicts=tuple(conflicts),
        incomplete=incomplete or bool(conflicts),
    )


def candidate_merge_pairs(graph: IdentityGraph) -> tuple[tuple[UUID, UUID], ...]:
    """Return review candidates only; caller cannot interpret this as a committed merge."""

    blocked = {
        frozenset((edge.left_node_id, edge.right_node_id))
        for edge in graph.edges
        if edge.relation
        in {
            IdentityRelation.CANNOT_BE_SAME,
            IdentityRelation.CORRECTED_DIFFERENT,
        }
    }
    return tuple(
        (edge.left_node_id, edge.right_node_id)
        for edge in graph.edges
        if edge.relation is IdentityRelation.SAME_CANDIDATE
        and frozenset((edge.left_node_id, edge.right_node_id)) not in blocked
    )
