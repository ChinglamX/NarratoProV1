"""Versioned policy/config/rights publication with explicit active pointers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, insert, select, update

import packages.persistence.schema as schema
from packages.contracts import RightsMetadata


class PublicationConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PublicationRef:
    registry_type: str
    registry_id: UUID
    version: int


def _canonical_checksum(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"sha256:{sha256(payload).hexdigest()}"


class PublicationRepository:
    def _activate(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        publication: PublicationRef,
        expected_pointer_version: int,
    ) -> None:
        pointer = (
            connection.execute(
                select(schema.publication_pointer)
                .where(
                    and_(
                        schema.publication_pointer.c.project_id == project_id,
                        schema.publication_pointer.c.registry_type == publication.registry_type,
                    )
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        current = int(pointer["version"]) if pointer is not None else 0
        if current != expected_pointer_version:
            raise PublicationConflict(
                f"expected publication version {expected_pointer_version}, actual {current}"
            )
        if pointer is None:
            connection.execute(
                insert(schema.publication_pointer).values(
                    project_id=project_id,
                    registry_type=publication.registry_type,
                    registry_id=publication.registry_id,
                    version=publication.version,
                )
            )
        else:
            result = connection.execute(
                update(schema.publication_pointer)
                .where(
                    and_(
                        schema.publication_pointer.c.project_id == project_id,
                        schema.publication_pointer.c.registry_type == publication.registry_type,
                        schema.publication_pointer.c.version == current,
                    )
                )
                .values(
                    registry_id=publication.registry_id,
                    version=publication.version,
                    row_version=schema.publication_pointer.c.row_version + 1,
                )
            )
            if result.rowcount != 1:
                raise PublicationConflict("publication pointer compare-and-swap failed")

    def publish_automation_policy(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        policy_id: UUID,
        version: int,
        scope: dict[str, Any],
        policy: dict[str, Any],
        expected_pointer_version: int,
    ) -> PublicationRef:
        if policy.get("level") not in {"L0", "L1", "L2", "L3", "L4"}:
            raise ValueError("automation policy requires a valid level")
        publication = PublicationRef("automation_policy", policy_id, version)
        with connection.begin_nested():
            connection.execute(
                insert(schema.automation_policy).values(
                    id=policy_id,
                    version=version,
                    scope_json=scope,
                    policy_json=policy,
                    state="published",
                )
            )
            self._activate(
                connection,
                project_id=project_id,
                publication=publication,
                expected_pointer_version=expected_pointer_version,
            )
        return publication

    def create_effective_config_snapshot(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        schema_version: str,
        resolved_config: dict[str, Any],
    ) -> PublicationRef:
        snapshot_id = uuid4()
        connection.execute(
            insert(schema.config_snapshot).values(
                id=snapshot_id,
                project_id=project_id,
                schema_version=schema_version,
                config_json=resolved_config,
                checksum=_canonical_checksum(resolved_config),
                state="committed",
            )
        )
        return PublicationRef("config_snapshot", snapshot_id, 1)

    def record_asset_rights(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        asset_ref: dict[str, Any],
        rights: RightsMetadata,
    ) -> UUID:
        rights_id = uuid4()
        connection.execute(
            insert(schema.asset_rights).values(
                id=rights_id,
                project_id=project_id,
                asset_ref=asset_ref,
                rights_json=rights.model_dump(mode="json"),
                state=rights.status.value,
                valid_until=rights.valid_until,
            )
        )
        return rights_id
