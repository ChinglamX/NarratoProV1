"""PostgreSQL artifact, dependency, and invalidation repository adapter."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, func, insert, select
from sqlalchemy.exc import IntegrityError

import packages.persistence.schema as schema
from packages.contracts import ArtifactDependency, ArtifactEnvelope, ArtifactRef


class ArtifactRepositoryError(RuntimeError):
    pass


class VersionConflict(ArtifactRepositoryError):
    pass


class DependencyCycle(ArtifactRepositoryError):
    pass


class ArtifactNotFound(ArtifactRepositoryError):
    pass


@dataclass(frozen=True, slots=True)
class RecomputePlan:
    decision_id: UUID
    root: ArtifactRef
    affected: tuple[ArtifactRef, ...]
    graph_version: int


def _ref_json(reference: ArtifactRef) -> dict[str, Any]:
    return reference.model_dump(mode="json", exclude_none=False)


class ArtifactRepository:
    def reserve(
        self,
        connection: Connection,
        *,
        artifact_id: UUID,
        project_id: UUID,
        artifact_type: str,
    ) -> None:
        connection.execute(
            insert(schema.artifact).values(
                id=artifact_id,
                project_id=project_id,
                artifact_type=artifact_type,
            )
        )

    def commit_version(
        self,
        connection: Connection,
        envelope: ArtifactEnvelope,
        *,
        expected_latest_version: int,
        blob_id: UUID | None = None,
    ) -> ArtifactRef:
        artifact_row = connection.execute(
            select(schema.artifact.c.artifact_type)
            .where(schema.artifact.c.id == envelope.artifact_id)
            .with_for_update()
        ).first()
        if artifact_row is None:
            raise ArtifactNotFound(str(envelope.artifact_id))
        if artifact_row.artifact_type != envelope.artifact_type:
            raise ArtifactRepositoryError("artifact type cannot change across versions")
        latest = connection.scalar(
            select(func.max(schema.artifact_version.c.version)).where(
                schema.artifact_version.c.artifact_id == envelope.artifact_id
            )
        )
        current = int(latest or 0)
        if current != expected_latest_version or envelope.version != current + 1:
            raise VersionConflict(
                f"expected latest {expected_latest_version}, actual {current}, "
                f"requested version {envelope.version}"
            )
        values = {
            "artifact_id": envelope.artifact_id,
            "version": envelope.version,
            "schema_version": envelope.schema_version,
            "run_id": envelope.run_id,
            "variant_id": envelope.variant_id,
            "state": envelope.state.value,
            "payload_json": envelope.payload,
            "blob_id": blob_id,
            "checksum": str(envelope.checksum),
            "producer_json": envelope.producer.model_dump(mode="json"),
            "rights_class": envelope.rights_class,
            "trace_id": envelope.trace_id.root,
            "created_at": envelope.created_at,
        }
        if envelope.payload is None and blob_id is None:
            raise ArtifactRepositoryError(
                "payload_uri must resolve to a committed blob before commit"
            )
        try:
            connection.execute(insert(schema.artifact_version).values(**values))
            if current == 0:
                connection.execute(
                    insert(schema.active_pointer).values(
                        artifact_id=envelope.artifact_id,
                        version=envelope.version,
                    )
                )
            else:
                updated = connection.execute(
                    schema.active_pointer.update()
                    .where(
                        and_(
                            schema.active_pointer.c.artifact_id == envelope.artifact_id,
                            schema.active_pointer.c.version == current,
                        )
                    )
                    .values(
                        version=envelope.version,
                        row_version=schema.active_pointer.c.row_version + 1,
                        updated_at=func.now(),
                    )
                )
                if updated.rowcount != 1:
                    raise VersionConflict("active pointer compare-and-swap failed")
            for item in envelope.inputs:
                self.add_dependency(
                    connection,
                    ArtifactDependency.model_validate(
                        {
                            "upstream": item,
                            "downstream": envelope.as_ref(),
                            "dependency_type": "semantic",
                            "invalidation_rule": "input-version-changed",
                        }
                    ),
                )
            connection.execute(
                insert(schema.outbox_event).values(
                    id=uuid4(),
                    aggregate_id=str(envelope.artifact_id),
                    event_type="artifact.committed",
                    payload_json={"artifact_ref": _ref_json(envelope.as_ref())},
                    trace_id=envelope.trace_id.root,
                )
            )
        except IntegrityError as error:
            raise VersionConflict("artifact version or checksum already committed") from error
        return envelope.as_ref()

    def get_version(self, connection: Connection, reference: ArtifactRef) -> dict[str, Any]:
        row = (
            connection.execute(
                select(schema.artifact_version).where(
                    and_(
                        schema.artifact_version.c.artifact_id == reference.artifact_id,
                        schema.artifact_version.c.version == reference.version,
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ArtifactNotFound(str(reference.artifact_id))
        return dict(row)

    def add_dependency(self, connection: Connection, edge: ArtifactDependency) -> None:
        if self._reachable(connection, edge.downstream, edge.upstream):
            raise DependencyCycle("dependency would create a cycle")
        connection.execute(
            insert(schema.dependency).values(
                upstream_artifact_id=edge.upstream.artifact_id,
                upstream_version=edge.upstream.version,
                downstream_artifact_id=edge.downstream.artifact_id,
                downstream_version=edge.downstream.version,
                dependency_type=edge.dependency_type.value,
                invalidation_rule=edge.invalidation_rule,
            )
        )

    def _reachable(
        self,
        connection: Connection,
        start: ArtifactRef,
        target: ArtifactRef,
        *,
        max_nodes: int = 100_000,
    ) -> bool:
        queue = deque([(start.artifact_id, start.version)])
        visited: set[tuple[UUID, int]] = set()
        target_key = (target.artifact_id, target.version)
        while queue:
            current = queue.popleft()
            if current == target_key:
                return True
            if current in visited:
                continue
            visited.add(current)
            if len(visited) > max_nodes:
                raise ArtifactRepositoryError("dependency traversal limit exceeded")
            rows = connection.execute(
                select(
                    schema.dependency.c.downstream_artifact_id,
                    schema.dependency.c.downstream_version,
                ).where(
                    and_(
                        schema.dependency.c.upstream_artifact_id == current[0],
                        schema.dependency.c.upstream_version == current[1],
                    )
                )
            )
            queue.extend((row.downstream_artifact_id, row.downstream_version) for row in rows)
        return False

    def invalidate(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        root: ArtifactRef,
        change_set: dict[str, Any],
        trace_id: str,
    ) -> RecomputePlan:
        connection.execute(select(func.pg_advisory_xact_lock(project_id.int & (2**63 - 1))))
        queue = deque([(root.artifact_id, root.version)])
        visited: set[tuple[UUID, int]] = {(root.artifact_id, root.version)}
        affected: list[ArtifactRef] = []
        while queue:
            current = queue.popleft()
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
                        schema.dependency.c.upstream_artifact_id == current[0],
                        schema.dependency.c.upstream_version == current[1],
                    )
                )
            )
            for row in rows:
                key = (row.downstream_artifact_id, row.downstream_version)
                if key in visited:
                    continue
                visited.add(key)
                reference = ArtifactRef.model_validate(
                    {
                        "artifact_id": row.downstream_artifact_id,
                        "version": row.downstream_version,
                        "artifact_type": row.artifact_type,
                        "checksum": row.checksum,
                    }
                )
                affected.append(reference)
                queue.append(key)
        graph_version = int(
            connection.scalar(select(func.count()).select_from(schema.dependency)) or 0
        )
        decision_id = uuid4()
        connection.execute(
            insert(schema.invalidation_decision).values(
                id=decision_id,
                project_id=project_id,
                root_ref=_ref_json(root),
                affected_refs=[_ref_json(item) for item in affected],
                graph_version=graph_version,
                change_set=change_set,
                trace_id=trace_id,
            )
        )
        return RecomputePlan(
            decision_id=decision_id,
            root=root,
            affected=tuple(affected),
            graph_version=graph_version,
        )
