"""Read-only Media Catalog boundary; corrections and approvals use canonical APIs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import Engine, and_, select

import packages.persistence.schema as schema
from packages.contracts import SceneShotCatalog

router = APIRouter(prefix="/v1/media-catalogs", tags=["media"])


@router.get("/{catalog_id}", response_model=SceneShotCatalog)
def get_media_catalog(
    catalog_id: UUID,
    request: Request,
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    version: int | None = None,
) -> SceneShotCatalog:
    if not {"viewer", "editor", "reviewer"}.intersection(actor_roles.split(",")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "catalog_forbidden"})
    engine: Engine = request.app.state.database_engine
    requested_version = version
    with engine.connect() as connection:
        if requested_version is None:
            requested_version = connection.scalar(
                select(schema.active_pointer.c.version).where(
                    schema.active_pointer.c.artifact_id == catalog_id
                )
            )
        payload = connection.scalar(
            select(schema.artifact_version.c.payload_json)
            .join(schema.artifact, schema.artifact.c.id == schema.artifact_version.c.artifact_id)
            .where(
                and_(
                    schema.artifact_version.c.artifact_id == catalog_id,
                    schema.artifact_version.c.version == requested_version,
                    schema.artifact.c.artifact_type == "SceneShotCatalog",
                )
            )
        )
    if not isinstance(payload, dict):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "catalog_not_found"})
    return SceneShotCatalog.model_validate(payload)
