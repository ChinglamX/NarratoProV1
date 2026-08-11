"""Master Timeline semantic patch endpoint."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import Engine

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
