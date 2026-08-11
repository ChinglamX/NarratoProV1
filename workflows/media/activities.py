"""Heartbeat-enabled media ingest Activity with bounded resource admission."""

import asyncio
from pathlib import Path
from uuid import UUID

from temporalio import activity

from apps.services.media_ingest import MediaIngestService
from packages.artifacts import LocalObjectStore
from packages.contracts import ArtifactRef, RightsMetadata
from packages.control.resource_admission import (
    ResourceAdmissionController,
    ResourceCapacity,
    ResourceRequest,
)
from packages.foundation.settings import get_settings
from packages.persistence.database import create_database_engine
from packages.providers.media import FFmpegMediaProvider
from workflows.media.models import MediaIngestActivityResult, MediaIngestWorkflowInput
from workflows.project.models import ArtifactPointer

_admission = ResourceAdmissionController(
    {
        "media": ResourceCapacity(
            cpu=16,
            memory_bytes=32 * 1024**3,
            gpu=0,
            disk_bytes=2 * 1024**4,
            cost_budget_micros=0,
            max_project_in_flight=1,
        )
    }
)


def _pointer(reference: ArtifactRef) -> ArtifactPointer:
    return ArtifactPointer(
        str(reference.artifact_id),
        reference.version,
        reference.artifact_type,
        str(reference.checksum) if reference.checksum else None,
    )


def _ingest_sync(request: MediaIngestWorkflowInput) -> MediaIngestActivityResult:
    source = Path(request.source_path).resolve(strict=True)
    if not source.is_file() or source.is_symlink():
        raise ValueError("workflow source is not a regular file")
    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    try:
        service = MediaIngestService(
            engine=engine,
            object_store=LocalObjectStore(settings.object_store_root),
            provider=FFmpegMediaProvider(),
        )
        profile = ArtifactRef.model_validate(
            {
                "artifact_id": request.profile.artifact_id,
                "version": request.profile.version,
                "artifact_type": request.profile.artifact_type,
                "checksum": request.profile.checksum,
            }
        )
        result = service.ingest(
            project_id=UUID(request.project_id),
            run_id=UUID(request.run_id),
            source_path=source,
            rights=RightsMetadata.model_validate(request.rights),
            profile_ref=profile,
            profile_version=request.profile_version,
            trace_id=request.trace_id,
        )
        return MediaIngestActivityResult(
            _pointer(result.source),
            _pointer(result.scene_shot_catalog),
            _pointer(result.frame_plan),
        )
    finally:
        engine.dispose()


@activity.defn
async def ingest_media_activity(request: MediaIngestWorkflowInput) -> MediaIngestActivityResult:
    lease_id = f"media:{request.run_id}"
    decision = _admission.admit(
        ResourceRequest(request.project_id, "media", cpu=2, memory_bytes=2 * 1024**3),
        lease_id=lease_id,
    )
    if not decision.admitted:
        raise RuntimeError(f"media resource admission rejected: {decision.reason}")
    activity.heartbeat({"stage": "media-ingest", "trace_id": request.trace_id})
    try:
        return await asyncio.to_thread(_ingest_sync, request)
    finally:
        _admission.release(lease_id)
