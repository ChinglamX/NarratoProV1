"""Deterministic contract-artifact commit helper shared by E09 application services.

Every E09 planning product is an immutable business artifact committed through
the canonical :class:`ArtifactRepository` boundary: content checksum over the
canonical JSON payload, exact-version input edges, and a transactional outbox
event emitted by the repository itself.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import Connection

from packages.contracts import ActorRef, ArtifactEnvelope, ArtifactRef
from packages.persistence.artifact_repository import ArtifactRepository


class ArtifactCommitError(RuntimeError):
    pass


def canonical_payload_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def payload_checksum(payload: Any) -> str:
    return "sha256:" + sha256(canonical_payload_bytes(payload)).hexdigest()


def commit_contract_artifact(
    connection: Connection,
    repository: ArtifactRepository,
    *,
    artifact_id: UUID,
    artifact_type: str,
    payload: Any,
    project_id: UUID,
    run_id: UUID,
    variant_id: UUID | None,
    trace_id: str,
    actor: ActorRef,
    producer_module: str,
    module_version: str,
    resource_profile_ref: ArtifactRef,
    rights_class: str,
    inputs: tuple[ArtifactRef, ...] = (),
    schema_version: str = "1.0.0",
) -> ArtifactRef:
    """Reserve an identity and commit version 1 of one contract artifact.

    The checksum is computed from the canonical JSON payload so that any
    downstream reader can re-derive and compare it.
    """

    if isinstance(payload, dict):
        payload_json = payload
    elif hasattr(payload, "model_dump"):
        payload_json = payload.model_dump(mode="json")
    else:
        raise ArtifactCommitError("payload must be a JSON object or contract model")
    repository.reserve(
        connection,
        artifact_id=artifact_id,
        project_id=project_id,
        artifact_type=artifact_type,
    )
    envelope = ArtifactEnvelope.model_validate(
        {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "schema_version": schema_version,
            "version": 1,
            "project_id": project_id,
            "run_id": run_id,
            "variant_id": variant_id,
            "state": "committed",
            "created_at": datetime.now(UTC),
            "created_by": actor,
            "inputs": inputs,
            "producer": {
                "module": producer_module,
                "module_version": module_version,
                "resource_profile_ref": resource_profile_ref,
            },
            "checksum": payload_checksum(payload_json),
            "rights_class": rights_class,
            "trace_id": trace_id,
            "payload": payload_json,
        }
    )
    return repository.commit_version(connection, envelope, expected_latest_version=0)
