"""Normalize persisted visual raw responses into an immutable VisualObservation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Engine

from packages.artifacts import ObjectStore
from packages.contracts import ArtifactEnvelope, ArtifactRef, ProviderIdentity, RawProviderResponse
from packages.intelligence.visual import normalize_visual_response
from packages.persistence import ArtifactRepository
from packages.persistence.database import transaction


class VisualObservationService:
    def __init__(self, *, engine: Engine, object_store: ObjectStore) -> None:
        self.engine = engine
        self.store = object_store
        self.artifacts = ArtifactRepository()

    def normalize_and_commit(
        self,
        *,
        observation_id: UUID,
        project_id: UUID,
        run_id: UUID,
        source_ref: ArtifactRef,
        frame_plan_ref: ArtifactRef,
        raw_response_ref: ArtifactRef,
        frame_evidence: dict[str, object],
        config_ref: ArtifactRef,
        resource_profile_ref: ArtifactRef,
        trace_id: str,
        rights_class: str,
    ) -> ArtifactRef:
        with self.engine.connect() as connection:
            raw_record = self.artifacts.get_version(connection, raw_response_ref)
        manifest = RawProviderResponse.model_validate(raw_record["payload_json"])
        with self.store.open(manifest.payload_uri) as source:
            provider_payload = json.load(source)
        if not isinstance(provider_payload, dict):
            raise ValueError("raw visual response must be an object")
        raw = {"frames": [{"frame": frame_evidence, **provider_payload}]}
        provider = ProviderIdentity.model_validate(manifest.provider)
        observation = normalize_visual_response(
            raw,
            source_ref=source_ref,
            frame_plan_ref=frame_plan_ref,
            raw_response_refs=[raw_response_ref],
            provider=provider,
        )
        encoded = observation.canonical_json().encode()
        envelope = ArtifactEnvelope.model_validate(
            {
                "artifact_id": observation_id,
                "artifact_type": "VisualObservation",
                "schema_version": "1.6.0",
                "version": 1,
                "project_id": project_id,
                "run_id": run_id,
                "state": "committed",
                "created_at": datetime.now(UTC),
                "created_by": {"kind": "system", "id": "visual-normalizer"},
                "inputs": [source_ref, frame_plan_ref, raw_response_ref],
                "producer": {
                    "module": "visual-normalizer",
                    "module_version": "1.0.0",
                    "provider": provider,
                    "config_refs": [config_ref],
                    "resource_profile_ref": resource_profile_ref,
                },
                "checksum": "sha256:" + sha256(encoded).hexdigest(),
                "rights_class": rights_class,
                "trace_id": trace_id,
                "payload": observation.model_dump(mode="json"),
            }
        )
        with transaction(self.engine) as connection:
            self.artifacts.reserve(
                connection,
                artifact_id=observation_id,
                project_id=project_id,
                artifact_type="VisualObservation",
            )
            return self.artifacts.commit_version(connection, envelope, expected_latest_version=0)
