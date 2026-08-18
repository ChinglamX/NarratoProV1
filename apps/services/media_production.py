"""E10 media production persistence: MixPlan / ASSArtifact / ConformReport."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from uuid import UUID, uuid4

from sqlalchemy import Connection

from packages.artifacts import ObjectStore
from packages.contracts import ActorRef, ArtifactRef
from packages.contracts.media_production import AlignmentArtifact, ConformReport, MixedAudio
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

    def persist_alignment(
        self,
        connection: Connection,
        *,
        alignment: AlignmentArtifact,
        project_id: UUID,
        run_id: UUID,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        alignment_id: UUID | None = None,
    ) -> ArtifactRef:
        return commit_contract_artifact(
            connection,
            self._artifacts,
            artifact_id=alignment_id or uuid4(),
            artifact_type="AlignmentArtifact",
            payload=alignment,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=trace_id,
            actor=actor,
            producer_module="media-production",
            module_version="e10-v1",
            resource_profile_ref=resource_profile_ref,
            rights_class="internal-preview",
            inputs=(alignment.voice_asset_ref, alignment.narration_line_set_ref),
        )

    def persist_conform_report(
        self,
        connection: Connection,
        *,
        report: ConformReport,
        project_id: UUID,
        run_id: UUID,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        report_id: UUID | None = None,
    ) -> ArtifactRef:
        return commit_contract_artifact(
            connection,
            self._artifacts,
            artifact_id=report_id or uuid4(),
            artifact_type="ConformReport",
            payload=report,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=trace_id,
            actor=actor,
            producer_module="media-production",
            module_version="e10-v1",
            resource_profile_ref=resource_profile_ref,
            rights_class="internal-preview",
            inputs=(
                report.source_timeline_ref,
                report.conformed_timeline_ref,
                report.voice_asset_ref,
                report.alignment_ref,
            ),
        )

    def persist_mixed_audio(
        self,
        connection: Connection,
        *,
        audio: bytes,
        mixed_audio: MixedAudio,
        project_id: UUID,
        run_id: UUID,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        mixed_audio_id: UUID | None = None,
    ) -> ArtifactRef:
        artifact_id = mixed_audio_id or uuid4()
        digest = "sha256:" + sha256(audio).hexdigest()
        staged = self._store.stage(run_id, f"mixed-audio-{artifact_id}", BytesIO(audio))
        registered = self._blobs.register_or_get_staged(
            connection, staged, content_type="audio/wav"
        )
        committed = self._blobs.commit(connection, self._store, registered)
        payload = mixed_audio.model_copy(update={"audio_blob_ref": committed.metadata.uri})
        from packages.contracts import ArtifactEnvelope

        self._artifacts.reserve(
            connection,
            artifact_id=artifact_id,
            project_id=project_id,
            artifact_type="MixedAudio",
        )
        envelope = ArtifactEnvelope.model_validate(
            {
                "artifact_id": artifact_id,
                "artifact_type": "MixedAudio",
                "schema_version": "1.0.0",
                "version": 1,
                "project_id": project_id,
                "run_id": run_id,
                "state": "committed",
                "created_at": datetime.now(UTC),
                "created_by": actor,
                "inputs": (mixed_audio.mix_plan_ref,),
                "producer": {
                    "module": "media-production",
                    "module_version": "e10-v1",
                    "resource_profile_ref": resource_profile_ref,
                },
                "checksum": digest,
                "rights_class": "internal-preview",
                "trace_id": trace_id,
                "payload": payload.model_dump(mode="json"),
            }
        )
        return self._artifacts.commit_version(
            connection,
            envelope,
            expected_latest_version=0,
            blob_id=committed.blob_id,
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
        registered = self._blobs.register_or_get_staged(
            connection, staged, content_type="text/plain; charset=utf-8"
        )
        committed = self._blobs.commit(connection, self._store, registered)
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
                    "blob_ref": committed.metadata.uri,
                },
            }
        )
        return self._artifacts.commit_version(
            connection, envelope, expected_latest_version=0, blob_id=committed.blob_id
        )
