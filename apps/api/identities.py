"""Identity review and human correction endpoints; never expose table writes."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import Engine

from packages.contracts import IdentityProposal
from packages.intelligence.identity import candidate_merge_pairs
from packages.intelligence.identity_corrections import (
    IdentityCorrectionConflict,
    preview_identity_correction,
)
from packages.persistence.database import transaction
from packages.persistence.identity_repository import (
    IdentityRepository,
    IdentityStorageConflict,
)

router = APIRouter(prefix="/v1/identity-graphs", tags=["identities"])


def _require_reviewer(roles_header: str) -> tuple[str, ...]:
    roles = tuple(sorted(item.strip() for item in roles_header.split(",") if item.strip()))
    if "story_reviewer" not in roles and "editor" not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "identity_forbidden"})
    return roles


@router.get("/{artifact_id}/versions/{version}/review")
def review_package(
    artifact_id: UUID,
    version: int,
    project_id: UUID,
    request: Request,
) -> dict[str, Any]:
    repository: IdentityRepository = request.app.state.identity_repository
    engine: Engine = request.app.state.database_engine
    from packages.contracts import ArtifactRef

    graph_ref = ArtifactRef.model_validate(
        {"artifact_id": artifact_id, "version": version, "artifact_type": "IdentityGraph"}
    )
    try:
        with engine.begin() as connection:
            snapshot = repository.lock_and_load(
                connection, project_id=project_id, graph_ref=graph_ref
            )
            downstream = repository.downstream_refs(connection, graph_ref)
    except IdentityStorageConflict as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "identity_stale"}) from error
    return {
        "graph_ref": graph_ref.model_dump(mode="json"),
        "graph": snapshot.graph.model_dump(mode="json"),
        "candidate_pairs": candidate_merge_pairs(snapshot.graph),
        "conflicts": [item.model_dump(mode="json") for item in snapshot.graph.conflicts],
        "downstream_refs": [item.model_dump(mode="json") for item in downstream],
    }


@router.post("/{artifact_id}/corrections:preview")
def preview(
    artifact_id: UUID,
    project_id: UUID,
    proposal: IdentityProposal,
    request: Request,
) -> dict[str, Any]:
    if proposal.base_graph_ref.artifact_id != artifact_id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "identity_mismatch"})
    repository: IdentityRepository = request.app.state.identity_repository
    engine: Engine = request.app.state.database_engine
    try:
        with engine.begin() as connection:
            snapshot = repository.lock_and_load(
                connection, project_id=project_id, graph_ref=proposal.base_graph_ref
            )
            impact = preview_identity_correction(
                graph_ref=snapshot.reference,
                graph=snapshot.graph,
                proposal=proposal,
                downstream_refs=repository.downstream_refs(connection, snapshot.reference),
            )
    except (IdentityStorageConflict, IdentityCorrectionConflict) as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "identity_conflict"}
        ) from error
    return impact.model_dump(mode="json")


@router.post("/{artifact_id}/corrections", status_code=status.HTTP_201_CREATED)
def apply(
    artifact_id: UUID,
    project_id: UUID,
    proposal: IdentityProposal,
    request: Request,
    actor_id: Annotated[str, Header(alias="X-Actor-Id")],
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> dict[str, Any]:
    roles = _require_reviewer(actor_roles)
    if proposal.base_graph_ref.artifact_id != artifact_id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "identity_mismatch"})
    repository: IdentityRepository = request.app.state.identity_repository
    engine: Engine = request.app.state.database_engine
    try:
        with transaction(engine) as connection:
            snapshot = repository.lock_and_load(
                connection, project_id=project_id, graph_ref=proposal.base_graph_ref
            )
            impact = preview_identity_correction(
                graph_ref=snapshot.reference,
                graph=snapshot.graph,
                proposal=proposal,
                downstream_refs=repository.downstream_refs(connection, snapshot.reference),
            )
            after_ref, plan = repository.apply(
                connection,
                project_id=project_id,
                proposal=proposal,
                resulting_graph=impact.resulting_graph,
                changed_character_ids=impact.changed_character_ids,
                actor={"actor_id": actor_id, "roles": roles},
                trace_id=trace_id,
            )
    except (IdentityStorageConflict, IdentityCorrectionConflict) as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "identity_conflict"}
        ) from error
    return {
        "after_ref": after_ref.model_dump(mode="json"),
        "invalidation_decision_id": plan.decision_id,
        "affected_refs": [item.model_dump(mode="json") for item in plan.affected],
    }
