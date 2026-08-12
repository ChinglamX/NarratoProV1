"""Application orchestration for policy-checked provider invocation and raw lineage."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from uuid import UUID

from sqlalchemy import Engine, and_, select

import packages.persistence.schema as schema
from packages.artifacts import ObjectStore
from packages.contracts import (
    ArtifactEnvelope,
    ArtifactRef,
    ProviderInvocationRequest,
    ProviderPackage,
    RawProviderResponse,
)
from packages.persistence import ArtifactRepository, BlobRepository
from packages.persistence.database import transaction
from packages.providers import InvocationPolicy, ProviderGateway, ProviderPort


class ProviderInvocationService:
    def __init__(self, *, engine: Engine, object_store: ObjectStore) -> None:
        self.engine = engine
        self.store = object_store
        self.gateway = ProviderGateway()
        self.artifacts = ArtifactRepository()
        self.blobs = BlobRepository()

    def invoke_and_record(
        self,
        *,
        provider: ProviderPort,
        request: ProviderInvocationRequest,
        policy: InvocationPolicy,
        raw_artifact_id: UUID,
        project_id: UUID,
        run_id: UUID,
        trace_id: str,
        rights_class: str,
    ) -> tuple[ArtifactRef, ProviderPackage]:
        package = provider.package()
        output = self.gateway.invoke(provider, request, policy)
        digest = "sha256:" + sha256(output.payload).hexdigest()
        request_digest = "sha256:" + sha256(request.canonical_json().encode()).hexdigest()
        with self.engine.connect() as connection:
            existing = connection.execute(
                select(schema.artifact_version.c.checksum).where(
                    and_(
                        schema.artifact_version.c.artifact_id == raw_artifact_id,
                        schema.artifact_version.c.version == 1,
                    )
                )
            ).first()
        if existing is not None:
            if existing.checksum != digest:
                raise RuntimeError("idempotent provider raw response checksum changed")
            return (
                ArtifactRef.model_validate(
                    {
                        "artifact_id": raw_artifact_id,
                        "version": 1,
                        "artifact_type": "RawProviderResponse",
                        "checksum": digest,
                    }
                ),
                package,
            )
        staged = self.store.stage(run_id, f"provider-{raw_artifact_id}", BytesIO(output.payload))
        try:
            with transaction(self.engine) as connection:
                registered = self.blobs.register_or_get_staged(
                    connection, staged, content_type=output.media_type
                )
                if registered.state == "committed":
                    self.store.delete_staged(staged.uri)
                    blob = registered
                else:
                    blob = self.blobs.commit(connection, self.store, registered)
                payload = RawProviderResponse.model_validate(
                    {
                        "provider": package.identity,
                        "capability": request.capability,
                        "request_checksum": request_digest,
                        "payload_uri": blob.metadata.uri,
                        "payload_checksum": digest,
                        "media_type": output.media_type,
                        "provider_schema_version": output.schema_version,
                        "redacted": False,
                    }
                )
                self.artifacts.reserve(
                    connection,
                    artifact_id=raw_artifact_id,
                    project_id=project_id,
                    artifact_type="RawProviderResponse",
                )
                envelope = ArtifactEnvelope.model_validate(
                    {
                        "artifact_id": raw_artifact_id,
                        "artifact_type": "RawProviderResponse",
                        "schema_version": "1.3.0",
                        "version": 1,
                        "project_id": project_id,
                        "run_id": run_id,
                        "state": "committed",
                        "created_at": datetime.now(UTC),
                        "created_by": {"kind": "system", "id": "provider-gateway"},
                        "inputs": request.inputs,
                        "producer": {
                            "module": "provider-gateway",
                            "module_version": "1.0.0",
                            "provider": package.identity,
                            "config_refs": [request.config_ref],
                            "resource_profile_ref": request.resource_profile_ref,
                        },
                        "checksum": digest,
                        "rights_class": rights_class,
                        "trace_id": trace_id,
                        "payload": payload.model_dump(mode="json"),
                    }
                )
                reference = self.artifacts.commit_version(
                    connection, envelope, expected_latest_version=0, blob_id=blob.blob_id
                )
        except Exception:
            self.store.delete_staged(staged.uri)
            raise
        return reference, package
