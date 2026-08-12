"""Transactional IdentityGraph successor commits and dependency impact discovery."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, func, insert, select, update
from sqlalchemy.exc import IntegrityError

import packages.persistence.schema as schema
from packages.contracts import ArtifactRef, IdentityGraph, IdentityProposal
from packages.intelligence.identity_corrections import preview_identity_correction
from packages.persistence.artifact_repository import ArtifactRepository, RecomputePlan


class IdentityStorageConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IdentitySnapshot:
    reference: ArtifactRef
    graph: IdentityGraph
    schema_version: str
    run_id: UUID
    variant_id: UUID | None
    producer: dict[str, Any]
    rights_class: str


class IdentityRepository:
    def __init__(self, artifacts: ArtifactRepository | None = None) -> None:
        self.artifacts = artifacts or ArtifactRepository()

    def lock_and_load(
        self, connection: Connection, *, project_id: UUID, graph_ref: ArtifactRef
    ) -> IdentitySnapshot:
        connection.execute(select(func.pg_advisory_xact_lock(project_id.int & (2**63 - 1))))
        pointer = connection.execute(
            select(schema.active_pointer)
            .where(schema.active_pointer.c.artifact_id == graph_ref.artifact_id)
            .with_for_update()
        ).first()
        if pointer is None or int(pointer.version) != graph_ref.version:
            raise IdentityStorageConflict("identity graph base version is stale")
        row = (
            connection.execute(
                select(schema.artifact_version).where(
                    and_(
                        schema.artifact_version.c.artifact_id == graph_ref.artifact_id,
                        schema.artifact_version.c.version == graph_ref.version,
                    )
                )
            )
            .mappings()
            .one()
        )
        payload = row["payload_json"]
        if not isinstance(payload, dict):
            raise IdentityStorageConflict("identity graph JSON payload is unavailable")
        return IdentitySnapshot(
            graph_ref,
            IdentityGraph.model_validate(payload),
            str(row["schema_version"]),
            row["run_id"],
            row["variant_id"],
            dict(row["producer_json"]),
            str(row["rights_class"]),
        )

    def downstream_refs(
        self, connection: Connection, graph_ref: ArtifactRef
    ) -> tuple[ArtifactRef, ...]:
        rows = connection.execute(
            select(
                schema.dependency.c.downstream_artifact_id,
                schema.dependency.c.downstream_version,
                schema.artifact.c.artifact_type,
                schema.artifact_version.c.checksum,
            )
            .join(
                schema.artifact,
                schema.artifact.c.id == schema.dependency.c.downstream_artifact_id,
            )
            .join(
                schema.artifact_version,
                and_(
                    schema.artifact_version.c.artifact_id
                    == schema.dependency.c.downstream_artifact_id,
                    schema.artifact_version.c.version == schema.dependency.c.downstream_version,
                ),
            )
            .where(
                and_(
                    schema.dependency.c.upstream_artifact_id == graph_ref.artifact_id,
                    schema.dependency.c.upstream_version == graph_ref.version,
                )
            )
        )
        return tuple(
            ArtifactRef(
                artifact_id=row.downstream_artifact_id,
                version=row.downstream_version,
                artifact_type=row.artifact_type,
                checksum=row.checksum,
            )
            for row in rows
        )

    def apply(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        proposal: IdentityProposal,
        actor: dict[str, Any],
        trace_id: str,
    ) -> tuple[ArtifactRef, RecomputePlan]:
        snapshot = self.lock_and_load(
            connection, project_id=project_id, graph_ref=proposal.base_graph_ref
        )
        impact = preview_identity_correction(
            graph_ref=snapshot.reference,
            graph=snapshot.graph,
            proposal=proposal,
            downstream_refs=self.downstream_refs(connection, snapshot.reference),
        )
        payload = impact.resulting_graph.model_dump(mode="json")
        encoded = impact.resulting_graph.canonical_bytes()
        checksum = "sha256:" + sha256(encoded).hexdigest()
        next_version = snapshot.reference.version + 1
        try:
            connection.execute(
                insert(schema.artifact_version).values(
                    artifact_id=snapshot.reference.artifact_id,
                    version=next_version,
                    schema_version=snapshot.schema_version,
                    run_id=snapshot.run_id,
                    variant_id=snapshot.variant_id,
                    state="committed",
                    payload_json=payload,
                    checksum=checksum,
                    producer_json={
                        "kind": "human_identity_correction",
                        "proposal_id": str(proposal.proposal_id),
                        "actor": actor,
                        "source_producer": snapshot.producer,
                    },
                    rights_class=snapshot.rights_class,
                    trace_id=trace_id,
                )
            )
            updated = connection.execute(
                update(schema.active_pointer)
                .where(
                    and_(
                        schema.active_pointer.c.artifact_id == snapshot.reference.artifact_id,
                        schema.active_pointer.c.version == snapshot.reference.version,
                    )
                )
                .values(
                    version=next_version,
                    row_version=schema.active_pointer.c.row_version + 1,
                )
            )
            if updated.rowcount != 1:
                raise IdentityStorageConflict("identity graph active pointer CAS failed")
            after_ref = ArtifactRef.model_validate(
                {
                    "artifact_id": snapshot.reference.artifact_id,
                    "version": next_version,
                    "artifact_type": "IdentityGraph",
                    "checksum": checksum,
                }
            )
            connection.execute(
                insert(schema.correction).values(
                    id=uuid4(),
                    project_id=project_id,
                    run_id=snapshot.run_id,
                    before_ref=snapshot.reference.model_dump(mode="json"),
                    after_ref=after_ref.model_dump(mode="json"),
                    semantic_operation=proposal.model_dump(mode="json"),
                    before_value=snapshot.graph.model_dump(mode="json"),
                    after_value=payload,
                    reason=proposal.reason,
                    reviewer_json=actor,
                )
            )
            connection.execute(
                insert(schema.outbox_event).values(
                    id=uuid4(),
                    aggregate_id=str(snapshot.reference.artifact_id),
                    event_type="identity.corrected",
                    payload_json={
                        "before_ref": snapshot.reference.model_dump(mode="json"),
                        "after_ref": after_ref.model_dump(mode="json"),
                    },
                    trace_id=trace_id,
                )
            )
        except IntegrityError as error:
            raise IdentityStorageConflict("identity graph successor commit conflicted") from error
        plan = self.artifacts.invalidate(
            connection,
            project_id=project_id,
            root=snapshot.reference,
            change_set={
                "proposal_id": str(proposal.proposal_id),
                "operation": proposal.operation.value,
                "changed_character_ids": [str(item) for item in impact.changed_character_ids],
            },
            trace_id=trace_id,
        )
        return after_ref, plan
