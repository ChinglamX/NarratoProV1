"""Asynchronous project/run command endpoints with idempotency."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from packages.persistence.command_repository import CommandRepository, IdempotencyConflict
from packages.persistence.database import transaction
from packages.persistence.project_repository import ProjectRepository

router = APIRouter(prefix="/v1", tags=["commands"])


class CreateProjectBody(BaseModel):
    name: str = Field(min_length=1, max_length=512)


class CreateRunBody(BaseModel):
    automation_policy: dict[str, Any]
    resource_profile: dict[str, Any]


class AcceptedCommand(BaseModel):
    command_id: UUID
    resource_id: UUID
    state: str
    delivery_pending: bool = False


def _checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@router.post("/projects", response_model=AcceptedCommand, status_code=status.HTTP_201_CREATED)
def create_project(
    body: CreateProjectBody,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> AcceptedCommand:
    engine: Engine = request.app.state.database_engine
    commands: CommandRepository = request.app.state.command_repository
    projects: ProjectRepository = request.app.state.project_repository
    payload = body.model_dump(mode="json")
    try:
        with transaction(engine) as connection:
            record = commands.register(
                connection,
                command_id=uuid4(),
                idempotency_key=idempotency_key,
                command_type="project.create",
                project_id=None,
                request=payload,
                request_checksum=_checksum(payload),
            )
            if record.response is not None:
                return AcceptedCommand.model_validate(record.response)
            project_id = uuid4()
            response = AcceptedCommand(
                command_id=record.command_id, resource_id=project_id, state="accepted"
            )
            projects.create_project(connection, project_id=project_id, name=body.name)
            commands.complete(
                connection,
                command_id=record.command_id,
                workflow_id=None,
                response=response.model_dump(mode="json"),
            )
    except IdempotencyConflict as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "idempotency_conflict"}
        ) from error
    return response


@router.post(
    "/projects/{project_id}/runs",
    response_model=AcceptedCommand,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_run(
    project_id: UUID,
    body: CreateRunBody,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> AcceptedCommand:
    engine: Engine = request.app.state.database_engine
    commands: CommandRepository = request.app.state.command_repository
    projects: ProjectRepository = request.app.state.project_repository
    payload = body.model_dump(mode="json") | {"project_id": str(project_id)}
    try:
        with transaction(engine) as connection:
            record = commands.register(
                connection,
                command_id=uuid4(),
                idempotency_key=idempotency_key,
                command_type="run.create",
                project_id=project_id,
                request=payload,
                request_checksum=_checksum(payload),
            )
            if record.response is not None:
                return AcceptedCommand.model_validate(record.response)
            run_id = uuid4()
            workflow_id = f"project-run/{project_id}/{run_id}"
            response = AcceptedCommand(
                command_id=record.command_id,
                resource_id=run_id,
                state="accepted",
                delivery_pending=True,
            )
            projects.create_run(
                connection,
                run_id=run_id,
                project_id=project_id,
                workflow_id=workflow_id,
                automation_policy_snapshot=body.automation_policy,
                resource_profile_snapshot=body.resource_profile,
                trace_id=trace_id,
            )
            commands.complete(
                connection,
                command_id=record.command_id,
                workflow_id=workflow_id,
                response=response.model_dump(mode="json"),
            )
    except IdempotencyConflict as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "idempotency_conflict"}
        ) from error
    return response
