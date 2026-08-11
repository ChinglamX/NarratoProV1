"""Timeline preview Activity: load exact Artifact pointer, compile, render and QC."""

from __future__ import annotations

import asyncio
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import and_, insert, select
from temporalio import activity

import packages.persistence.schema as schema
from packages.contracts import ArtifactRef, MasterTimeline
from packages.foundation.settings import get_settings
from packages.persistence.database import create_database_engine
from packages.production import render_fake_preview
from packages.timeline import compile_render_plan
from workflows.timeline.models import PreviewActivityResult, PreviewWorkflowInput


def _render_preview_sync(request: PreviewWorkflowInput) -> PreviewActivityResult:
    engine = create_database_engine(get_settings().database_url)
    try:
        with engine.connect() as connection:
            payload = connection.scalar(
                select(schema.artifact_version.c.payload_json).where(
                    and_(
                        schema.artifact_version.c.artifact_id == request.timeline.artifact_id,
                        schema.artifact_version.c.version == request.timeline.version,
                    )
                )
            )
    finally:
        engine.dispose()
    if not isinstance(payload, dict):
        raise ValueError("timeline artifact payload is unavailable")
    timeline = MasterTimeline.model_validate(payload)
    timeline_ref = ArtifactRef.model_validate(
        {
            "artifact_id": request.timeline.artifact_id,
            "version": request.timeline.version,
            "artifact_type": request.timeline.artifact_type,
            "checksum": request.timeline.checksum,
        }
    )
    profile_ref = ArtifactRef.model_validate(
        {
            "artifact_id": request.profile.artifact_id,
            "version": request.profile.version,
            "artifact_type": request.profile.artifact_type,
            "checksum": request.profile.checksum,
        }
    )
    plan = compile_render_plan(
        timeline,
        timeline_ref=timeline_ref,
        profile_ref=profile_ref,
        toolchain_version="ffmpeg-8.1.2",
    )
    result = render_fake_preview(timeline, Path(request.output_path))
    digest = "sha256:" + sha256(result.output_path.read_bytes()).hexdigest()
    engine = create_database_engine(get_settings().database_url)
    try:
        with engine.begin() as connection:
            preview_id = (
                connection.scalar(
                    select(schema.artifact.c.id)
                    .join(
                        schema.dependency,
                        schema.dependency.c.downstream_artifact_id == schema.artifact.c.id,
                    )
                    .where(
                        and_(
                            schema.dependency.c.upstream_artifact_id
                            == UUID(request.timeline.artifact_id),
                            schema.dependency.c.upstream_version == request.timeline.version,
                            schema.artifact.c.artifact_type == "ProxyRender",
                        )
                    )
                    .limit(1)
                )
                or uuid4()
            )
            existing = connection.scalar(
                select(schema.artifact_version.c.checksum).where(
                    and_(
                        schema.artifact_version.c.artifact_id == preview_id,
                        schema.artifact_version.c.version == 1,
                    )
                )
            )
            if existing is not None and str(existing) != digest:
                raise ValueError("idempotent preview checksum changed")
            if existing is None:
                connection.execute(
                    insert(schema.artifact).values(
                        id=preview_id,
                        project_id=UUID(request.project_id),
                        artifact_type="ProxyRender",
                    )
                )
                connection.execute(
                    insert(schema.artifact_version).values(
                        artifact_id=preview_id,
                        version=1,
                        schema_version="1.0.0",
                        run_id=UUID(request.run_id),
                        state="committed",
                        payload_json={
                            "output_path": str(result.output_path),
                            "subtitle_path": str(result.subtitle_path),
                            "qc": {
                                "video_codec": result.video_codec,
                                "audio_codec": result.audio_codec,
                                "width": result.width,
                                "height": result.height,
                            },
                        },
                        checksum=digest,
                        producer_json={"kind": "fake_preview", "plan_checksum": plan.checksum},
                        rights_class="internal-preview",
                        trace_id=request.trace_id,
                    )
                )
                connection.execute(
                    insert(schema.active_pointer).values(artifact_id=preview_id, version=1)
                )
                connection.execute(
                    insert(schema.dependency).values(
                        upstream_artifact_id=UUID(request.timeline.artifact_id),
                        upstream_version=request.timeline.version,
                        downstream_artifact_id=preview_id,
                        downstream_version=1,
                        dependency_type="generation",
                        invalidation_rule="timeline-version-changed",
                    )
                )
                connection.execute(
                    insert(schema.outbox_event).values(
                        id=uuid4(),
                        aggregate_id=str(preview_id),
                        event_type="preview.committed",
                        payload_json={"artifact_id": str(preview_id), "version": 1},
                        trace_id=request.trace_id,
                    )
                )
    finally:
        engine.dispose()
    return PreviewActivityResult(
        preview=type(request.timeline)(
            artifact_id=str(preview_id),
            version=1,
            artifact_type="ProxyRender",
            checksum=digest,
        ),
        subtitle_path=str(result.subtitle_path),
        qc={
            "video_codec": result.video_codec,
            "audio_codec": result.audio_codec,
            "width": result.width,
            "height": result.height,
        },
    )


@activity.defn
async def render_preview_activity(request: PreviewWorkflowInput) -> PreviewActivityResult:
    activity.heartbeat({"stage": "render", "trace_id": request.trace_id})
    return await asyncio.to_thread(_render_preview_sync, request)
