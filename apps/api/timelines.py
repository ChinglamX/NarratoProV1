"""Master Timeline semantic patch, version navigation and partial preview."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Connection, Engine

from apps.services.timeline_editing import (
    TimelineEditingError,
    TimelineEditingService,
)
from packages.artifacts.object_store import LocalObjectStore
from packages.contracts import MasterTimeline, TimelinePatch
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.database import transaction
from packages.persistence.timeline_repository import (
    TimelineStorageConflict,
)
from packages.production.real_preview import (
    PreviewRenderError,
    compute_changed_ranges,
    render_partial_preview,
)

router = APIRouter(prefix="/v1/timelines", tags=["timelines"])


class JumpRequest(BaseModel):
    version: int = Field(ge=1)


class PartialPreviewRequest(BaseModel):
    """Render the changed ranges between two timeline versions."""

    from_version: int = Field(ge=1)
    to_version: int = Field(ge=1)


@router.post("/{timeline_id}/patches", status_code=status.HTTP_201_CREATED)
def apply_timeline_patch(
    timeline_id: UUID,
    patch: TimelinePatch,
    request: Request,
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> dict[str, object]:
    _require_editor(actor_roles)
    try:
        result = _editing_service(request).apply_patch(
            timeline_id=timeline_id,
            patch=patch,
            trace_id=trace_id,
        )
    except TimelineEditingError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "timeline_conflict", "message": str(error)},
        ) from error
    return {
        "timeline_id": result.timeline_id,
        "version": result.version,
        "checksum": result.checksum,
        "rebased": result.rebased,
        "changes": [
            {
                "item_id": str(change.item_id),
                "change": change.change,
                "before_version": change.before_version,
                "after_version": change.after_version,
            }
            for change in result.changes
        ],
    }


def _require_editor(actor_roles: str) -> None:
    if "editor" not in {role.strip() for role in actor_roles.split(",")}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "timeline_forbidden"})


def _editing_service(request: Request) -> TimelineEditingService:
    service: TimelineEditingService = request.app.state.timeline_editing_service
    return service


@router.post("/{timeline_id}/undo")
def undo_timeline(
    timeline_id: UUID,
    request: Request,
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> dict[str, object]:
    _require_editor(actor_roles)
    try:
        result = _editing_service(request).undo(
            timeline_id=timeline_id, trace_id=trace_id, reason="api:undo"
        )
    except TimelineEditingError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "timeline_conflict", "message": str(error)}
        ) from error
    return {
        "timeline_id": result.timeline_id,
        "version": result.version,
        "previous_version": result.previous_version,
        "reason": result.reason,
    }


@router.post("/{timeline_id}/redo")
def redo_timeline(
    timeline_id: UUID,
    request: Request,
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> dict[str, object]:
    _require_editor(actor_roles)
    try:
        result = _editing_service(request).redo(
            timeline_id=timeline_id, trace_id=trace_id, reason="api:redo"
        )
    except TimelineEditingError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "timeline_conflict", "message": str(error)}
        ) from error
    return {
        "timeline_id": result.timeline_id,
        "version": result.version,
        "previous_version": result.previous_version,
        "reason": result.reason,
    }


@router.post("/{timeline_id}/jump")
def jump_timeline(
    timeline_id: UUID,
    body: JumpRequest,
    request: Request,
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> dict[str, object]:
    _require_editor(actor_roles)
    try:
        result = _editing_service(request).jump_to_version(
            timeline_id=timeline_id,
            target_version=body.version,
            trace_id=trace_id,
            reason="api:jump",
        )
    except TimelineEditingError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "timeline_conflict", "message": str(error)}
        ) from error
    return {
        "timeline_id": result.timeline_id,
        "version": result.version,
        "previous_version": result.previous_version,
        "reason": result.reason,
    }


@router.get("/{timeline_id}/versions")
def list_timeline_versions(
    timeline_id: UUID,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    include_changes: Annotated[bool, Query()] = True,
) -> dict[str, object]:
    service = _editing_service(request)
    versions = service.list_versions(
        timeline_id=timeline_id, limit=limit, include_changes=include_changes
    )
    return {
        "timeline_id": timeline_id,
        "count": len(versions),
        "versions": [
            {
                "version": v.version,
                "producer": v.producer,
                "changes": [
                    {
                        "item_id": str(c.item_id),
                        "change": c.change,
                        "before_version": c.before_version,
                        "after_version": c.after_version,
                    }
                    for c in (v.changes or ())
                ],
            }
            for v in versions
        ],
    }


@router.get("/{timeline_id}/diff")
def diff_timeline_versions(
    timeline_id: UUID,
    request: Request,
    from_version: Annotated[int, Query(ge=1)],
    to_version: Annotated[int, Query(ge=1)],
) -> dict[str, object]:
    service = _editing_service(request)
    try:
        changes = service.diff_versions(
            timeline_id=timeline_id,
            from_version=from_version,
            to_version=to_version,
        )
    except TimelineEditingError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail={"code": "version_not_found", "message": str(error)}
        ) from error
    return {
        "timeline_id": timeline_id,
        "from_version": from_version,
        "to_version": to_version,
        "changes": [
            {
                "item_id": str(c.item_id),
                "change": c.change,
                "before_version": c.before_version,
                "after_version": c.after_version,
            }
            for c in changes
        ],
    }


@router.get("/{timeline_id}/current")
def get_current_timeline(
    timeline_id: UUID,
    request: Request,
) -> dict[str, object]:
    service = _editing_service(request)
    try:
        timeline = service.get_current(timeline_id=timeline_id)
    except TimelineStorageConflict as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail={"code": "timeline_not_found"}
        ) from error
    return timeline.model_dump(mode="json")


def _resolve_source_paths(
    connection: Connection,
    repository: ArtifactRepository,
    store: LocalObjectStore,
    timeline: MasterTimeline,
) -> dict[UUID, Path]:
    """Resolve object-store URIs for every source media referenced by the timeline.

    Mirrors the worker activity resolution so the API renders the same real
    media files the workflow would use.
    """
    paths: dict[UUID, Path] = {}
    for track in timeline.tracks:
        for item in track.items:
            source_ref = item.source_ref
            if source_ref is None or source_ref.artifact_id in paths:
                continue
            payload = repository.get_version(connection, source_ref)["payload_json"]
            uri = payload.get("uri")
            if not uri:
                raise PreviewRenderError("source media payload has no object-store uri")
            paths[source_ref.artifact_id] = store.local_path(str(uri))
    return paths


@router.post("/{timeline_id}/preview-partial", status_code=status.HTTP_201_CREATED)
def render_timeline_partial_preview(
    timeline_id: UUID,
    body: PartialPreviewRequest,
    request: Request,
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
) -> dict[str, object]:
    """Render only the ranges that changed between two timeline versions.

    The server resolves the real source media from the object store, computes
    the changed time ranges from the semantic diff, and renders the first
    changed range. The full range list is returned so clients can render
    additional segments.
    """
    _require_editor(actor_roles)
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "ffmpeg_unavailable"}
        )
    service = _editing_service(request)
    try:
        from_timeline = service.get_version(timeline_id=timeline_id, version=body.from_version)
        to_timeline = service.get_version(timeline_id=timeline_id, version=body.to_version)
    except TimelineEditingError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "version_not_found", "message": str(error)},
        ) from error
    ranges = compute_changed_ranges(from_timeline, to_timeline)
    if not ranges:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "no_changes", "message": "timeline versions are identical"},
        )
    engine: Engine = request.app.state.database_engine
    try:
        with transaction(engine) as connection:
            source_paths = _resolve_source_paths(
                connection,
                ArtifactRepository(),
                LocalObjectStore(get_settings().object_store_root),
                to_timeline,
            )
    except PreviewRenderError as error:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "source_unavailable", "message": str(error)},
        ) from error
    output_path = (
        Path(get_settings().temp_root) / f"timeline-{timeline_id}-v{body.to_version}-preview.mp4"
    )
    try:
        result = render_partial_preview(
            to_timeline, source_paths, output_path, time_range=ranges[0]
        )
    except PreviewRenderError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "preview_failed", "message": str(error)},
        ) from error
    return {
        "timeline_id": str(timeline_id),
        "from_version": body.from_version,
        "to_version": body.to_version,
        "output_path": str(result.output_path),
        "subtitle_path": str(result.subtitle_path),
        "original_start": result.original_start,
        "original_end": result.original_end,
        "duration_seconds": result.duration_seconds,
        "clip_count": result.clip_count,
        "changed_ranges": [[start, end] for start, end in ranges],
    }
