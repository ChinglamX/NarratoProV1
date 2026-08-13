"""Master Timeline semantic patch endpoint."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import Engine

from apps.services.timeline_editing import (
    TimelineEditingError,
    TimelineEditingService,
)
from packages.contracts import MasterTimeline, TimelinePatch
from packages.persistence.database import transaction
from packages.persistence.timeline_repository import (
    TimelineRepository,
    TimelineStorageConflict,
)
from packages.timeline import (
    TimelinePatchConflict,
    apply_patch,
    can_rebase,
    semantic_diff,
    validate_timeline,
)

router = APIRouter(prefix="/v1/timelines", tags=["timelines"])


class JumpRequest(BaseModel):
    version: int


class PartialPreviewRequest(BaseModel):
    start: float
    end: float


@router.post("/{timeline_id}/patches", status_code=status.HTTP_201_CREATED)
def apply_timeline_patch(
    timeline_id: UUID,
    patch: TimelinePatch,
    request: Request,
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> dict[str, object]:
    if "editor" not in {role.strip() for role in actor_roles.split(",")}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "timeline_forbidden"})
    engine: Engine = request.app.state.database_engine
    repository: TimelineRepository = request.app.state.timeline_repository
    try:
        with transaction(engine) as connection:
            if patch.base_timeline.artifact_id != timeline_id:
                raise TimelinePatchConflict("patch base does not match timeline identity")
            base_snapshot, current_snapshot = repository.lock_and_load(
                connection,
                artifact_id=timeline_id,
                base_version=patch.base_timeline.version,
            )
            base = MasterTimeline.model_validate(base_snapshot.payload)
            current = MasterTimeline.model_validate(current_snapshot.payload)
            rebased = base_snapshot.version != current_snapshot.version
            if rebased and not can_rebase(patch, semantic_diff(base, current)):
                raise TimelinePatchConflict("concurrent patch touches the same item")
            candidate = apply_patch(current, patch)
            if not validate_timeline(candidate).render_ready:
                raise TimelinePatchConflict("timeline validation failed")
            payload = candidate.model_dump(mode="json")
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
            checksum = "sha256:" + sha256(encoded).hexdigest()
            version = repository.commit(
                connection,
                artifact_id=timeline_id,
                current=current_snapshot,
                payload=payload,
                checksum=checksum,
                patch_id=patch.patch_id,
                rebased=rebased,
                trace_id=trace_id,
            )
    except (TimelinePatchConflict, TimelineStorageConflict) as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "timeline_conflict"}
        ) from error
    return {
        "timeline_id": timeline_id,
        "version": version,
        "checksum": checksum,
        "rebased": rebased,
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
