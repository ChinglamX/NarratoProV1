"""E05 media ingest vertical application service."""

from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from sqlalchemy import Engine, and_, select
from sqlalchemy.exc import IntegrityError

import packages.persistence.schema as schema
from packages.artifacts import LocalObjectStore
from packages.contracts import (
    ArtifactEnvelope,
    ArtifactRef,
    FrameSamplePlan,
    MediaAsset,
    RightsMetadata,
    SceneShotCatalog,
)
from packages.persistence import ArtifactRepository, BlobRepository, MediaIdentityRepository
from packages.persistence.database import transaction
from packages.providers.media import FFmpegMediaProvider, detect_scenes


@dataclass(frozen=True, slots=True)
class MediaIngestResult:
    source: ArtifactRef
    probe: ArtifactRef
    proxy: ArtifactRef
    audio: ArtifactRef | None
    frame_plan: ArtifactRef
    scene_shot_catalog: ArtifactRef
    reused_source: bool
    derivative_count: int


class MediaIngestService:
    def __init__(
        self,
        *,
        engine: Engine,
        object_store: LocalObjectStore,
        provider: FFmpegMediaProvider,
    ) -> None:
        self.engine = engine
        self.store = object_store
        self.provider = provider
        self.artifacts = ArtifactRepository()
        self.blobs = BlobRepository()
        self.identities = MediaIdentityRepository()

    def _identity(
        self,
        *,
        project_id: UUID,
        source_checksum: str,
        profile_version: str,
        role: str,
    ) -> tuple[UUID, bool]:
        with transaction(self.engine) as connection:
            return self.identities.resolve(
                connection,
                project_id=project_id,
                source_checksum=source_checksum,
                profile_version=profile_version,
                role=role,
            )

    def _commit_payload(
        self,
        *,
        project_id: UUID,
        run_id: UUID,
        artifact_id: UUID,
        artifact_type: str,
        payload: dict[str, object],
        checksum: str,
        profile_ref: ArtifactRef,
        trace_id: str,
        inputs: tuple[ArtifactRef, ...] = (),
        blob_id: UUID | None = None,
    ) -> tuple[ArtifactRef, bool]:
        with transaction(self.engine) as connection:
            existing = connection.execute(
                select(schema.artifact_version.c.checksum).where(
                    and_(
                        schema.artifact_version.c.artifact_id == artifact_id,
                        schema.artifact_version.c.version == 1,
                    )
                )
            ).first()
            if existing is not None:
                return (
                    ArtifactRef.model_validate(
                        {
                            "artifact_id": artifact_id,
                            "version": 1,
                            "artifact_type": artifact_type,
                            "checksum": existing.checksum,
                        }
                    ),
                    True,
                )
            try:
                self.artifacts.reserve(
                    connection,
                    artifact_id=artifact_id,
                    project_id=project_id,
                    artifact_type=artifact_type,
                )
            except IntegrityError:
                raise RuntimeError("deterministic artifact identity collision") from None
            envelope = ArtifactEnvelope.model_validate(
                {
                    "artifact_id": artifact_id,
                    "artifact_type": artifact_type,
                    "schema_version": "1.0.0",
                    "version": 1,
                    "project_id": project_id,
                    "run_id": run_id,
                    "state": "committed",
                    "created_at": datetime.now(UTC),
                    "created_by": {"kind": "system", "id": "media-ingest"},
                    "inputs": inputs,
                    "producer": {
                        "module": "media-ingest",
                        "module_version": "1.0.0",
                        "resource_profile_ref": profile_ref,
                    },
                    "checksum": checksum,
                    "rights_class": "ingest-snapshot",
                    "trace_id": trace_id,
                    "payload": payload,
                }
            )
            return self.artifacts.commit_version(
                connection, envelope, expected_latest_version=0, blob_id=blob_id
            ), False

    def _store_file(
        self, source: Path, *, run_id: UUID, activity_id: str, content_type: str
    ) -> tuple[str, str, UUID]:
        with source.open("rb") as stream:
            staged = self.store.stage(run_id, activity_id, stream)
        with transaction(self.engine) as connection:
            registered = self.blobs.register_or_get_staged(
                connection, staged, content_type=content_type
            )
            if registered.state == "committed":
                self.store.delete_staged(staged.uri)
                return (
                    registered.metadata.uri,
                    registered.metadata.checksum,
                    registered.blob_id,
                )
            committed = self.blobs.commit(connection, self.store, registered)
            return committed.metadata.uri, committed.metadata.checksum, committed.blob_id

    def ingest(
        self,
        *,
        project_id: UUID,
        run_id: UUID,
        source_path: Path,
        rights: RightsMetadata,
        profile_ref: ArtifactRef,
        profile_version: str,
        trace_id: str,
    ) -> MediaIngestResult:
        if not source_path.is_file() or source_path.is_symlink():
            raise ValueError("source must be a readable regular file")
        probe = self.provider.probe(source_path)
        uri, source_checksum, source_blob_id = self._store_file(
            source_path,
            run_id=run_id,
            activity_id="source",
            content_type=mimetypes.guess_type(source_path.name)[0] or "application/octet-stream",
        )
        source_id, source_identity_reused = self._identity(
            project_id=project_id,
            source_checksum=source_checksum,
            profile_version="source-v1",
            role="source",
        )
        source_asset = MediaAsset.model_validate(
            {
                "asset_id": source_id,
                "role": "source",
                "uri": uri,
                "checksum": source_checksum,
                "technical": probe.technical,
                "rights": rights,
            }
        )
        source_ref, reused = self._commit_payload(
            project_id=project_id,
            run_id=run_id,
            artifact_id=source_id,
            artifact_type="SourceMedia",
            payload=source_asset.model_dump(mode="json"),
            checksum=source_checksum,
            profile_ref=profile_ref,
            trace_id=trace_id,
            blob_id=source_blob_id,
        )
        probe_checksum = (
            "sha256:" + hashlib.sha256(json.dumps(probe.raw, sort_keys=True).encode()).hexdigest()
        )
        probe_id, _ = self._identity(
            project_id=project_id,
            source_checksum=source_checksum,
            profile_version=profile_version,
            role="probe",
        )
        probe_ref, _ = self._commit_payload(
            project_id=project_id,
            run_id=run_id,
            artifact_id=probe_id,
            artifact_type="MediaProbe",
            payload={
                "normalized": probe.technical.model_dump(mode="json"),
                "raw": probe.raw,
                "provider_version": probe.ffprobe_version,
            },
            checksum=probe_checksum,
            profile_ref=profile_ref,
            trace_id=trace_id,
            inputs=(source_ref,),
        )
        with TemporaryDirectory() as temporary:
            derivatives = self.provider.derive(source_path, Path(temporary), probe)
            proxy_ref = self._commit_derivative(
                derivatives.proxy_path,
                role="proxy",
                artifact_type="ProxyMedia",
                source_ref=source_ref,
                project_id=project_id,
                run_id=run_id,
                rights=rights,
                profile_ref=profile_ref,
                profile_version=profile_version,
                trace_id=trace_id,
            )
            audio_ref = (
                self._commit_derivative(
                    derivatives.audio_path,
                    role="original_audio",
                    artifact_type="AudioStem",
                    source_ref=source_ref,
                    project_id=project_id,
                    run_id=run_id,
                    rights=rights,
                    profile_ref=profile_ref,
                    profile_version=profile_version,
                    trace_id=trace_id,
                )
                if derivatives.audio_path
                else None
            )
            boundaries = detect_scenes(derivatives.proxy_path)
            segments = []
            for boundary in boundaries:
                start_us = round(float(boundary.start_seconds) * 1_000_000)
                duration_us = round(
                    float(boundary.end_seconds - boundary.start_seconds) * 1_000_000
                )
                segments.append(
                    {
                        "segment_id": uuid4(),
                        "kind": "shot",
                        "source": source_ref,
                        "source_range": {
                            "start": {"value": start_us, "rate_num": 1_000_000},
                            "duration": {"value": duration_us, "rate_num": 1_000_000},
                        },
                        "detector": {
                            "provider": "local",
                            "implementation": "pyscenedetect-adaptive",
                            "version": "0.7.1",
                            "license": "BSD-3-Clause",
                        },
                        "confidence": {
                            "score": 0.5,
                            "status": "shadow",
                            "method": "adaptive-detector-v1",
                            "applicable_scope": "shot-boundary:v1",
                            "risk_class": "medium",
                        },
                        "status": "detected",
                    }
                )
            catalog = SceneShotCatalog.model_validate({"source": source_ref, "segments": segments})
            catalog_id, _ = self._identity(
                project_id=project_id,
                source_checksum=source_checksum,
                profile_version=profile_version,
                role="scene-shot-catalog",
            )
            catalog_ref, _ = self._commit_payload(
                project_id=project_id,
                run_id=run_id,
                artifact_id=catalog_id,
                artifact_type="SceneShotCatalog",
                payload=catalog.model_dump(mode="json"),
                checksum="sha256:" + hashlib.sha256(catalog.canonical_json().encode()).hexdigest(),
                profile_ref=profile_ref,
                trace_id=trace_id,
                inputs=(source_ref, proxy_ref),
            )
            samples = []
            frame_assets = []
            for index, frame_path in enumerate(derivatives.frame_paths):
                frame_uri, frame_checksum, _ = self._store_file(
                    frame_path,
                    run_id=run_id,
                    activity_id=f"frame-{index:05d}",
                    content_type="image/jpeg",
                )
                samples.append(
                    {
                        "sample_id": uuid4(),
                        "source_time": {"value": index * 30_000_000, "rate_num": 1_000_000},
                        "frame_index": index,
                        "reason": "uniform-baseline",
                    }
                )
                frame_assets.append(
                    {
                        "sample_id": str(samples[-1]["sample_id"]),
                        "uri": frame_uri,
                        "checksum": frame_checksum,
                    }
                )
            plan = FrameSamplePlan.model_validate(
                {
                    "source": source_ref,
                    "purpose": "quality",
                    "profile_ref": profile_ref,
                    "samples": samples,
                    "parameters": {
                        "interval_seconds": 30,
                        "mapping": "source-clock",
                        "frame_assets": frame_assets,
                    },
                }
            )
            plan_id, _ = self._identity(
                project_id=project_id,
                source_checksum=source_checksum,
                profile_version=profile_version,
                role="frame-sample-plan",
            )
            plan_ref, _ = self._commit_payload(
                project_id=project_id,
                run_id=run_id,
                artifact_id=plan_id,
                artifact_type="FrameSamplePlan",
                payload=plan.model_dump(mode="json"),
                checksum="sha256:" + hashlib.sha256(plan.canonical_json().encode()).hexdigest(),
                profile_ref=profile_ref,
                trace_id=trace_id,
                inputs=(source_ref, proxy_ref),
            )
        return MediaIngestResult(
            source_ref,
            probe_ref,
            proxy_ref,
            audio_ref,
            plan_ref,
            catalog_ref,
            reused or source_identity_reused,
            4 + int(audio_ref is not None),
        )

    def _commit_derivative(
        self,
        path: Path,
        *,
        role: str,
        artifact_type: str,
        source_ref: ArtifactRef,
        project_id: UUID,
        run_id: UUID,
        rights: RightsMetadata,
        profile_ref: ArtifactRef,
        profile_version: str,
        trace_id: str,
    ) -> ArtifactRef:
        probe = self.provider.probe(path)
        uri, checksum, blob_id = self._store_file(
            path,
            run_id=run_id,
            activity_id=role,
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        )
        artifact_id, _ = self._identity(
            project_id=project_id,
            source_checksum=str(source_ref.checksum or ""),
            profile_version=profile_version,
            role=role,
        )
        asset = MediaAsset.model_validate(
            {
                "asset_id": artifact_id,
                "role": role,
                "uri": uri,
                "checksum": checksum,
                "technical": probe.technical,
                "rights": rights,
                "source_ref": source_ref,
                "derivation_profile_ref": profile_ref,
            }
        )
        reference, _ = self._commit_payload(
            project_id=project_id,
            run_id=run_id,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            payload=asset.model_dump(mode="json"),
            checksum=checksum,
            profile_ref=profile_ref,
            trace_id=trace_id,
            inputs=(source_ref,),
            blob_id=blob_id,
        )
        return reference
