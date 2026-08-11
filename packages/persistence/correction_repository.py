"""Generic semantic correction adapter creating immutable artifact successors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, insert, select, update

import packages.persistence.schema as schema


class CorrectionConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    correction_id: UUID
    artifact_id: UUID
    version: int
    checksum: str
    downstream_refs: tuple[dict[str, Any], ...]


def _apply_operations(source: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    result = json.loads(json.dumps(source))
    for operation in operations:
        path = operation.get("path")
        if (
            not isinstance(path, list)
            or not path
            or not all(isinstance(item, str) for item in path)
        ):
            raise CorrectionConflict("operation path must be a non-empty string array")
        cursor = result
        for segment in path[:-1]:
            child = cursor.get(segment)
            if not isinstance(child, dict):
                raise CorrectionConflict("operation path does not exist")
            cursor = child
        leaf = path[-1]
        kind = operation.get("operation")
        if kind == "add":
            if leaf in cursor:
                raise CorrectionConflict("add target already exists")
            cursor[leaf] = operation.get("value")
        elif kind == "replace":
            if leaf not in cursor:
                raise CorrectionConflict("replace target does not exist")
            cursor[leaf] = operation.get("value")
        elif kind == "remove":
            if leaf not in cursor:
                raise CorrectionConflict("remove target does not exist")
            del cursor[leaf]
        else:
            raise CorrectionConflict("unsupported semantic operation")
    return cast(dict[str, Any], result)


class CorrectionRepository:
    def preview(
        self,
        connection: Connection,
        *,
        artifact_id: UUID,
        base_version: int,
        operations: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
        row = (
            connection.execute(
                select(schema.artifact_version).where(
                    and_(
                        schema.artifact_version.c.artifact_id == artifact_id,
                        schema.artifact_version.c.version == base_version,
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None or not isinstance(row["payload_json"], dict):
            raise CorrectionConflict("base artifact payload is unavailable")
        downstream = connection.execute(
            select(
                schema.dependency.c.downstream_artifact_id,
                schema.dependency.c.downstream_version,
            ).where(
                and_(
                    schema.dependency.c.upstream_artifact_id == artifact_id,
                    schema.dependency.c.upstream_version == base_version,
                )
            )
        )
        refs = tuple(
            {"artifact_id": str(item.downstream_artifact_id), "version": item.downstream_version}
            for item in downstream
        )
        return _apply_operations(dict(row["payload_json"]), operations), refs

    def apply(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        run_id: UUID,
        artifact_id: UUID,
        base_version: int,
        operations: list[dict[str, Any]],
        reason: str,
        reviewer_snapshot: dict[str, Any],
        trace_id: str,
    ) -> CorrectionResult:
        pointer = connection.execute(
            select(schema.active_pointer)
            .where(schema.active_pointer.c.artifact_id == artifact_id)
            .with_for_update()
        ).first()
        if pointer is None or int(pointer.version) != base_version:
            raise CorrectionConflict("base version is stale")
        before = (
            connection.execute(
                select(schema.artifact_version).where(
                    and_(
                        schema.artifact_version.c.artifact_id == artifact_id,
                        schema.artifact_version.c.version == base_version,
                    )
                )
            )
            .mappings()
            .one()
        )
        if not isinstance(before["payload_json"], dict):
            raise CorrectionConflict("blob-only artifact cannot use JSON semantic patch")
        after_payload, downstream = self.preview(
            connection,
            artifact_id=artifact_id,
            base_version=base_version,
            operations=operations,
        )
        encoded = json.dumps(
            after_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
        checksum = "sha256:" + sha256(encoded).hexdigest()
        next_version = base_version + 1
        connection.execute(
            insert(schema.artifact_version).values(
                artifact_id=artifact_id,
                version=next_version,
                schema_version=before["schema_version"],
                run_id=run_id,
                variant_id=before["variant_id"],
                state="committed",
                payload_json=after_payload,
                blob_id=None,
                checksum=checksum,
                producer_json={
                    "kind": "human_correction",
                    "source_producer": before["producer_json"],
                },
                rights_class=before["rights_class"],
                trace_id=trace_id,
            )
        )
        updated = connection.execute(
            update(schema.active_pointer)
            .where(
                and_(
                    schema.active_pointer.c.artifact_id == artifact_id,
                    schema.active_pointer.c.version == base_version,
                )
            )
            .values(
                version=next_version,
                row_version=schema.active_pointer.c.row_version + 1,
            )
        )
        if updated.rowcount != 1:
            raise CorrectionConflict("active pointer compare-and-swap failed")
        correction_id = uuid4()
        connection.execute(
            insert(schema.correction).values(
                id=correction_id,
                project_id=project_id,
                run_id=run_id,
                before_ref={"artifact_id": str(artifact_id), "version": base_version},
                after_ref={"artifact_id": str(artifact_id), "version": next_version},
                semantic_operation={"operations": operations},
                before_value=before["payload_json"],
                after_value=after_payload,
                reason=reason,
                reviewer_json=reviewer_snapshot,
            )
        )
        connection.execute(
            insert(schema.outbox_event).values(
                id=uuid4(),
                aggregate_id=str(artifact_id),
                event_type="artifact.corrected",
                payload_json={
                    "artifact_id": str(artifact_id),
                    "version": next_version,
                    "downstream_refs": list(downstream),
                },
                trace_id=trace_id,
            )
        )
        return CorrectionResult(correction_id, artifact_id, next_version, checksum, downstream)
