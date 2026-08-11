"""Semantic correction preview/apply API."""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from packages.persistence.correction_repository import CorrectionConflict, CorrectionRepository
from packages.persistence.database import transaction

router = APIRouter(prefix="/v1/artifacts", tags=["corrections"])


class OperationBody(BaseModel):
    operation: Literal["add", "replace", "remove"]
    path: list[str] = Field(min_length=1)
    value: Any = None


class PatchBody(BaseModel):
    project_id: UUID
    run_id: UUID
    base_version: int = Field(ge=1)
    operations: list[OperationBody] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=4096)


def _operations(body: PatchBody) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in body.operations]


@router.post("/{artifact_id}/patches:preview")
def preview(
    artifact_id: UUID,
    body: PatchBody,
    request: Request,
) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: CorrectionRepository = request.app.state.correction_repository
    try:
        with engine.connect() as connection:
            result, downstream = repository.preview(
                connection,
                artifact_id=artifact_id,
                base_version=body.base_version,
                operations=_operations(body),
            )
    except CorrectionConflict as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "patch_conflict"}) from error
    return {"valid": True, "result": result, "downstream_refs": downstream}


@router.post("/{artifact_id}/patches", status_code=status.HTTP_201_CREATED)
def apply(
    artifact_id: UUID,
    body: PatchBody,
    request: Request,
    actor_id: Annotated[str, Header(alias="X-Actor-Id")],
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> dict[str, Any]:
    roles = {item.strip() for item in actor_roles.split(",")}
    if "editor" not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "correction_forbidden"})
    engine: Engine = request.app.state.database_engine
    repository: CorrectionRepository = request.app.state.correction_repository
    try:
        with transaction(engine) as connection:
            result = repository.apply(
                connection,
                project_id=body.project_id,
                run_id=body.run_id,
                artifact_id=artifact_id,
                base_version=body.base_version,
                operations=_operations(body),
                reason=body.reason,
                reviewer_snapshot={"actor_id": actor_id, "roles": sorted(roles)},
                trace_id=trace_id,
            )
    except CorrectionConflict as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "patch_conflict"}) from error
    return {
        "correction_id": result.correction_id,
        "artifact_id": result.artifact_id,
        "version": result.version,
        "checksum": result.checksum,
        "downstream_refs": result.downstream_refs,
    }
