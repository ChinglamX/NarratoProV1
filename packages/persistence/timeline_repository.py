"""Persistence primitives for optimistic Master Timeline successor commits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, func, insert, select, update
from sqlalchemy.exc import IntegrityError

import packages.persistence.schema as schema


class TimelineStorageConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TimelineSnapshot:
    version: int
    payload: dict[str, Any]
    schema_version: str
    run_id: UUID
    variant_id: UUID | None
    producer: dict[str, Any]
    rights_class: str


class TimelineRepository:
    def lock_and_load(
        self,
        connection: Connection,
        *,
        artifact_id: UUID,
        base_version: int,
    ) -> tuple[TimelineSnapshot, TimelineSnapshot]:
        pointer = connection.execute(
            select(schema.active_pointer)
            .where(schema.active_pointer.c.artifact_id == artifact_id)
            .with_for_update()
        ).first()
        if pointer is None:
            raise TimelineStorageConflict("timeline does not exist")
        current_version = int(pointer.version)
        rows = {
            int(row["version"]): row
            for row in connection.execute(
                select(schema.artifact_version).where(
                    and_(
                        schema.artifact_version.c.artifact_id == artifact_id,
                        schema.artifact_version.c.version.in_({base_version, current_version}),
                    )
                )
            )
            .mappings()
            .all()
        }
        if base_version not in rows or current_version not in rows:
            raise TimelineStorageConflict("timeline base/current version is unavailable")

        def snapshot(version: int) -> TimelineSnapshot:
            row = rows[version]
            payload = row["payload_json"]
            if not isinstance(payload, dict):
                raise TimelineStorageConflict("timeline JSON payload is unavailable")
            return TimelineSnapshot(
                version,
                dict(payload),
                str(row["schema_version"]),
                row["run_id"],
                row["variant_id"],
                dict(row["producer_json"]),
                str(row["rights_class"]),
            )

        return snapshot(base_version), snapshot(current_version)

    def commit(
        self,
        connection: Connection,
        *,
        artifact_id: UUID,
        current: TimelineSnapshot,
        payload: dict[str, Any],
        checksum: str,
        patch_id: UUID,
        rebased: bool,
        trace_id: str,
    ) -> int:
        # Append-only version allocation: the caller holds the active_pointer
        # row lock (see lock_and_load), so max(version)+1 is race-free. This
        # keeps undo/redo navigation safe: editing after an undo appends a NEW
        # version instead of reusing the undone number (artifact_version PK is
        # artifact_id+version and versions are immutable once written).
        max_version = connection.scalar(
            select(func.max(schema.artifact_version.c.version)).where(
                schema.artifact_version.c.artifact_id == artifact_id
            )
        )
        next_version = (int(max_version) + 1) if max_version is not None else 1
        try:
            connection.execute(
                insert(schema.artifact_version).values(
                    artifact_id=artifact_id,
                    version=next_version,
                    schema_version=current.schema_version,
                    run_id=current.run_id,
                    variant_id=current.variant_id,
                    state="committed",
                    payload_json=payload,
                    checksum=checksum,
                    producer_json={
                        "kind": "timeline_patch",
                        "patch_id": str(patch_id),
                        "source_producer": current.producer,
                    },
                    rights_class=current.rights_class,
                    trace_id=trace_id,
                )
            )
            updated = connection.execute(
                update(schema.active_pointer)
                .where(
                    and_(
                        schema.active_pointer.c.artifact_id == artifact_id,
                        schema.active_pointer.c.version == current.version,
                    )
                )
                .values(
                    version=next_version,
                    row_version=schema.active_pointer.c.row_version + 1,
                )
            )
            if updated.rowcount != 1:
                raise TimelineStorageConflict("timeline active pointer CAS failed")
            connection.execute(
                insert(schema.outbox_event).values(
                    id=uuid4(),
                    aggregate_id=str(artifact_id),
                    event_type="timeline.patched",
                    payload_json={
                        "artifact_id": str(artifact_id),
                        "version": next_version,
                        "patch_id": str(patch_id),
                        "rebased": rebased,
                    },
                    trace_id=trace_id,
                )
            )
        except IntegrityError as error:
            raise TimelineStorageConflict("timeline version commit conflicted") from error
        return next_version

    def set_active_version(
        self,
        connection: Connection,
        *,
        artifact_id: UUID,
        target_version: int,
        expected_version: int,
        trace_id: str,
        reason: str,
    ) -> int:
        """Move the active pointer to an existing version (undo/redo/jump).

        Uses compare-and-swap on ``expected_version`` to prevent concurrent
        navigation races. The target version must already exist in
        ``artifact_version``.
        """
        exists = connection.execute(
            select(schema.artifact_version).where(
                and_(
                    schema.artifact_version.c.artifact_id == artifact_id,
                    schema.artifact_version.c.version == target_version,
                )
            )
        ).first()
        if exists is None:
            raise TimelineStorageConflict(
                f"target timeline version {target_version} does not exist"
            )
        updated = connection.execute(
            update(schema.active_pointer)
            .where(
                and_(
                    schema.active_pointer.c.artifact_id == artifact_id,
                    schema.active_pointer.c.version == expected_version,
                )
            )
            .values(
                version=target_version,
                row_version=schema.active_pointer.c.row_version + 1,
            )
        )
        if updated.rowcount != 1:
            raise TimelineStorageConflict("timeline active pointer CAS failed")
        connection.execute(
            insert(schema.outbox_event).values(
                id=uuid4(),
                aggregate_id=str(artifact_id),
                event_type="timeline.version_navigated",
                payload_json={
                    "artifact_id": str(artifact_id),
                    "from_version": expected_version,
                    "to_version": target_version,
                    "reason": reason,
                },
                trace_id=trace_id,
            )
        )
        return target_version

    def list_versions(
        self,
        connection: Connection,
        *,
        artifact_id: UUID,
        limit: int = 100,
    ) -> list[TimelineSnapshot]:
        """List timeline versions newest-first, up to ``limit``."""
        rows = (
            connection.execute(
                select(schema.artifact_version)
                .where(schema.artifact_version.c.artifact_id == artifact_id)
                .order_by(schema.artifact_version.c.version.desc())
                .limit(limit)
            )
            .mappings()
            .all()
        )
        snapshots: list[TimelineSnapshot] = []
        for row in rows:
            payload = row["payload_json"]
            if not isinstance(payload, dict):
                continue
            snapshots.append(
                TimelineSnapshot(
                    version=int(row["version"]),
                    payload=dict(payload),
                    schema_version=str(row["schema_version"]),
                    run_id=row["run_id"],
                    variant_id=row["variant_id"],
                    producer=dict(row["producer_json"]) if row["producer_json"] else {},
                    rights_class=str(row["rights_class"]),
                )
            )
        return snapshots

    def get_active_version(self, connection: Connection, *, artifact_id: UUID) -> int:
        """Return the current active version number."""
        pointer = connection.execute(
            select(schema.active_pointer).where(schema.active_pointer.c.artifact_id == artifact_id)
        ).first()
        if pointer is None:
            raise TimelineStorageConflict("timeline does not exist")
        return int(pointer.version)

    def approved_intent_version(self, connection: Connection, *, artifact_id: UUID) -> int | None:
        """Return the version approved as the timeline intent, if any.

        The approved intent is the exact version referenced by the
        ``approved_timeline_intent`` publication pointer (set only by an L1
        human approve decision). Editing that version is blocked by the
        service until a new review cycle approves a successor.
        """
        row = connection.execute(
            select(schema.publication_pointer).where(
                and_(
                    schema.publication_pointer.c.registry_type == "approved_timeline_intent",
                    schema.publication_pointer.c.registry_id == artifact_id,
                )
            )
        ).first()
        if row is None:
            return None
        return int(row.version)
