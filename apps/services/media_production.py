"""E10 media production persistence: MixPlan / ASSArtifact / ConformReport."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from uuid import UUID, uuid4

from sqlalchemy import Connection

from packages.artifacts import ObjectStore
from packages.contracts import ActorRef, ArtifactRef
from packages.persistence import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.blob_repository import BlobRepository


class MediaProductionService:
    def __init__(self, *, artifacts: ArtifactRepository, store: ObjectStore) -> None:
        self._artifacts = artifacts
        self._store = store
        self._blobs = BlobRepository()

    def persist_mix_plan(
        self,
        connection: Connection,
        *,
        mix_plan: object,
        project_id: UUID,
        run_id: UUID,
        variant_id: UUID | None,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        inputs: tuple[ArtifactRef, ...],
        rights_class: str,
        mix_plan_id: UUID | None = None,
    ) -> ArtifactRef:
        return commit_contract_artifact(
            connection,
            self._artifacts,
            artifact_id=mix_plan_id or uuid4(),
            artifact_type="MixPlan",
            payload=mix_plan,
            project_id=project_id,
            run_id=run_id,
            variant_id=variant_id,
            trace_id=trace_id,
            actor=actor,
            producer_module="media-production",
            module_version="e10-v1",
            resource_profile_ref=resource_profile_ref,
            rights_class=rights_class,
            inputs=inputs,
        )

    def persist_ass_artifact(
        self,
        connection: Connection,
        *,
        ass_content: str,
        subtitle_cue_set_ref: ArtifactRef,
        libass_profile_ref: ArtifactRef,
        project_id: UUID,
        run_id: UUID,
        variant_id: UUID | None,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        rights_class: str,
        ass_artifact_id: UUID | None = None,
    ) -> ArtifactRef:
        """Persist ASS text as an Object Store blob and commit an ASSArtifact."""
        from packages.contracts import ArtifactEnvelope

        digest = "sha256:" + sha256(ass_content.encode()).hexdigest()
        staged = self._store.stage(
            run_id, f"ass-{ass_artifact_id or uuid4()}", BytesIO(ass_content.encode())
        )
        blob = self._blobs.register_or_get_staged(
            connection, staged, content_type="text/plain; charset=utf-8"
        )
        self._store.commit(staged.uri, digest)
        artifact_id = ass_artifact_id or uuid4()
        self._artifacts.reserve(
            connection, artifact_id=artifact_id, project_id=project_id, artifact_type="ASSArtifact"
        )
        envelope = ArtifactEnvelope.model_validate(
            {
                "artifact_id": artifact_id,
                "artifact_type": "ASSArtifact",
                "schema_version": "1.0.0",
                "version": 1,
                "project_id": project_id,
                "run_id": run_id,
                "state": "committed",
                "created_at": datetime.now(UTC),
                "created_by": actor,
                "inputs": (subtitle_cue_set_ref, libass_profile_ref),
                "producer": {
                    "module": "media-production",
                    "module_version": "e10-v1",
                    "resource_profile_ref": resource_profile_ref,
                },
                "checksum": digest,
                "rights_class": rights_class,
                "trace_id": trace_id,
                "payload": {
                    "subtitle_cue_set_ref": subtitle_cue_set_ref.model_dump(mode="json"),
                    "libass_profile_ref": libass_profile_ref.model_dump(mode="json"),
                    "blob_ref": staged.uri,
                },
            }
        )
        return self._artifacts.commit_version(
            connection, envelope, expected_latest_version=0, blob_id=blob.blob_id
        )
