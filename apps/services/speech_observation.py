"""Normalize a persisted raw speech response into an immutable SpeechObservation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Engine

from packages.artifacts import ObjectStore
from packages.contracts import (
    ArtifactEnvelope,
    ArtifactRef,
    ProviderIdentity,
    RawProviderResponse,
)
from packages.intelligence.speech import normalize_funasr_response
from packages.persistence import ArtifactRepository
from packages.persistence.database import transaction


class SpeechObservationService:
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
        source_audio_ref: ArtifactRef,
        raw_response_ref: ArtifactRef,
        config_ref: ArtifactRef,
        resource_profile_ref: ArtifactRef,
        trace_id: str,
        rights_class: str,
    ) -> ArtifactRef:
        with self.engine.connect() as connection:
            raw_record = self.artifacts.get_version(connection, raw_response_ref)
        raw_manifest = RawProviderResponse.model_validate(raw_record["payload_json"])
        with self.store.open(raw_manifest.payload_uri) as source:
            raw = json.load(source)
        if not isinstance(raw, dict):
            raise ValueError("raw speech response must be a JSON object")
        provider = ProviderIdentity.model_validate(raw_manifest.provider)
        observation = normalize_funasr_response(
            raw,
            source_audio_ref=source_audio_ref,
            raw_response_ref=raw_response_ref,
            provider=provider,
        )
        encoded = observation.canonical_json().encode()
        checksum = "sha256:" + sha256(encoded).hexdigest()
        envelope = ArtifactEnvelope.model_validate(
            {
                "artifact_id": observation_id,
                "artifact_type": "SpeechObservation",
                "schema_version": "1.5.0",
                "version": 1,
                "project_id": project_id,
                "run_id": run_id,
                "state": "committed",
                "created_at": datetime.now(UTC),
                "created_by": {"kind": "system", "id": "speech-normalizer"},
                "inputs": [source_audio_ref, raw_response_ref],
                "producer": {
                    "module": "speech-normalizer",
                    "module_version": "1.0.0",
                    "provider": provider,
                    "config_refs": [config_ref],
                    "resource_profile_ref": resource_profile_ref,
                },
                "checksum": checksum,
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
                artifact_type="SpeechObservation",
            )
            return self.artifacts.commit_version(connection, envelope, expected_latest_version=0)
