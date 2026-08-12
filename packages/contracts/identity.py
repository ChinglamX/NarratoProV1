"""Project-local identity graph contracts; similarity never establishes legal identity."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.evidence import ConfidenceRecord, EvidenceLink
from packages.contracts.foundation import UUID, ArtifactRef, StableName, TimeRange


class IdentityNodeKind(StrEnum):
    FACE_OBSERVATION = "face_observation"
    PERSON_TRACKLET = "person_tracklet"
    SPEAKER_CLUSTER = "speaker_cluster"
    NAME_MENTION = "name_mention"
    KNOWN_CHARACTER_SEED = "known_character_seed"


class IdentityRelation(StrEnum):
    SAME_CANDIDATE = "same_candidate"
    CANNOT_BE_SAME = "cannot_be_same"
    SPEAKS_AS = "speaks_as"
    VISIBLE_DURING = "visible_during"
    NAMED_AS = "named_as"
    CORRECTED_SAME = "corrected_same"
    CORRECTED_DIFFERENT = "corrected_different"


class IdentityConflictSeverity(StrEnum):
    BLOCKER = "blocker"
    REVIEW = "review"
    WARNING = "warning"


class IdentityNode(StrictContract):
    node_id: UUID
    kind: IdentityNodeKind
    observation_ref: ArtifactRef
    source_ranges: tuple[TimeRange, ...]
    label_hint: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    evidence: tuple[EvidenceLink, ...]

    @model_validator(mode="after")
    def require_grounding(self) -> Self:
        if not self.source_ranges or any(item.is_empty for item in self.source_ranges):
            raise ValueError("identity node requires non-empty source ranges")
        if not self.evidence:
            raise ValueError("identity node requires evidence")
        return self


class IdentityEdge(StrictContract):
    edge_id: UUID
    left_node_id: UUID
    right_node_id: UUID
    relation: IdentityRelation
    evidence: tuple[EvidenceLink, ...]
    confidence: ConfidenceRecord
    created_by_human: bool = False

    @model_validator(mode="after")
    def require_valid_edge(self) -> Self:
        if self.left_node_id == self.right_node_id:
            raise ValueError("identity edge cannot point to itself")
        if not self.evidence:
            raise ValueError("identity edge requires evidence")
        corrected = self.relation in {
            IdentityRelation.CORRECTED_SAME,
            IdentityRelation.CORRECTED_DIFFERENT,
        }
        if corrected and not self.created_by_human:
            raise ValueError("corrected identity edges require a human source")
        return self


class CharacterIdentity(StrictContract):
    character_id: UUID
    display_name: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    aliases: tuple[Annotated[str, Field(min_length=1, max_length=512)], ...] = ()
    member_node_ids: tuple[UUID, ...]
    temporary: bool
    evidence: tuple[EvidenceLink, ...]

    @model_validator(mode="after")
    def require_members_and_name_semantics(self) -> Self:
        if not self.member_node_ids or len(self.member_node_ids) != len(set(self.member_node_ids)):
            raise ValueError("character identity requires unique member nodes")
        if not self.evidence:
            raise ValueError("character identity requires evidence")
        if not self.temporary and self.display_name is None:
            raise ValueError("non-temporary character requires a display name")
        return self


class IdentityConflict(StrictContract):
    conflict_id: UUID
    conflict_type: StableName
    severity: IdentityConflictSeverity
    node_ids: tuple[UUID, ...]
    edge_ids: tuple[UUID, ...]
    detail: Annotated[str, Field(min_length=1, max_length=4_096)]
    evidence: tuple[EvidenceLink, ...]
    unresolved: bool = True

    @model_validator(mode="after")
    def require_targets(self) -> Self:
        if len(set(self.node_ids)) < 2:
            raise ValueError("identity conflict requires at least two nodes")
        return self


class IdentityGraph(StrictContract):
    source_observation_refs: tuple[ArtifactRef, ...]
    nodes: tuple[IdentityNode, ...]
    edges: tuple[IdentityEdge, ...]
    characters: tuple[CharacterIdentity, ...]
    conflicts: tuple[IdentityConflict, ...] = ()
    applied_proposal_ids: tuple[UUID, ...] = ()
    incomplete: bool = False

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("identity node ids must be unique")
        known = set(node_ids)
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("identity edge ids must be unique")
        if any(
            edge.left_node_id not in known or edge.right_node_id not in known for edge in self.edges
        ):
            raise ValueError("identity edge references unknown node")
        member_ids = [
            member for character in self.characters for member in character.member_node_ids
        ]
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("identity node cannot belong to multiple characters")
        if not set(member_ids) <= known:
            raise ValueError("character references unknown identity node")
        if any(not set(conflict.node_ids) <= known for conflict in self.conflicts):
            raise ValueError("identity conflict references unknown node")
        if len(self.applied_proposal_ids) != len(set(self.applied_proposal_ids)):
            raise ValueError("applied identity proposal ids must be unique")
        return self


class IdentityProposalOperation(StrEnum):
    MERGE = "merge"
    SPLIT = "split"
    ASSIGN_NAME = "assign_name"
    UNASSIGN_NAME = "unassign_name"


class IdentityProposal(StrictContract):
    proposal_id: UUID
    base_graph_ref: ArtifactRef
    operation: IdentityProposalOperation
    character_ids: tuple[UUID, ...]
    node_ids: tuple[UUID, ...]
    proposed_name: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    reason: Annotated[str, Field(min_length=1, max_length=2_048)]
    evidence: tuple[EvidenceLink, ...]
    confidence: ConfidenceRecord

    @model_validator(mode="after")
    def validate_operation(self) -> Self:
        if not self.evidence:
            raise ValueError("identity proposal requires evidence")
        if self.operation is IdentityProposalOperation.ASSIGN_NAME and self.proposed_name is None:
            raise ValueError("assign_name proposal requires proposed_name")
        if self.operation is not IdentityProposalOperation.ASSIGN_NAME and self.proposed_name:
            raise ValueError("proposed_name is only valid for assign_name")
        if self.operation is IdentityProposalOperation.MERGE and len(self.character_ids) < 2:
            raise ValueError("merge proposal requires at least two characters")
        if self.operation is IdentityProposalOperation.SPLIT and len(self.node_ids) < 1:
            raise ValueError("split proposal requires node ids")
        return self


class IdentityReviewPackage(StrictContract):
    graph_ref: ArtifactRef
    graph: IdentityGraph
    candidate_pairs: tuple[tuple[UUID, UUID], ...]
    conflicts: tuple[IdentityConflict, ...]
    downstream_refs: tuple[ArtifactRef, ...] = ()

    @model_validator(mode="after")
    def require_exact_graph_type(self) -> Self:
        if self.graph_ref.artifact_type != "IdentityGraph":
            raise ValueError("identity review requires IdentityGraph ref")
        return self


class IdentityCorrectionResult(StrictContract):
    before_ref: ArtifactRef
    after_ref: ArtifactRef | None = None
    proposal: IdentityProposal
    resulting_graph: IdentityGraph
    affected_refs: tuple[ArtifactRef, ...] = ()
    changed_character_ids: tuple[UUID, ...]
    committed: bool = False
