"""Review command API; decisions are committed before signal delivery."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from packages.control.reviews import (
    ReviewConflict,
    ReviewDecision,
    Reviewer,
    ReviewForbidden,
)
from packages.persistence.database import transaction
from packages.persistence.review_repository import (
    ReviewRepository,
    StoredReviewConflict,
    StoredReviewForbidden,
)

router = APIRouter(prefix="/v1/reviews", tags=["reviews"])


class DecisionBody(BaseModel):
    expected_target_version: int = Field(ge=1)
    decision: ReviewDecision
    reasons: list[dict[str, Any]] = Field(default_factory=list)


class DecisionResponse(BaseModel):
    decision_id: UUID
    review_id: UUID
    state: str
    delivery_pending: bool


@router.post(
    "/{review_id}/decision",
    response_model=DecisionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_decision(
    review_id: UUID,
    body: DecisionBody,
    request: Request,
    actor_id: Annotated[str, Header(alias="X-Actor-Id")],
    actor_roles: Annotated[str, Header(alias="X-Actor-Roles")],
    actor_type: Annotated[str, Header(alias="X-Actor-Type")] = "human",
    trace_id: Annotated[str, Header(alias="X-Trace-Id")] = "0" * 32,
) -> DecisionResponse:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    reviewer = Reviewer(
        actor_id=actor_id,
        roles=frozenset(role.strip() for role in actor_roles.split(",") if role.strip()),
        service_account=actor_type == "service",
    )
    try:
        with transaction(engine) as connection:
            result = repository.decide(
                connection,
                review_id=review_id,
                expected_target_version=body.expected_target_version,
                decision=body.decision.value,
                reviewer_snapshot={
                    "actor_id": reviewer.actor_id,
                    "roles": sorted(reviewer.roles),
                    "service_account": reviewer.service_account,
                },
                reasons=body.reasons,
                trace_id=trace_id,
            )
    except (ReviewForbidden, StoredReviewForbidden) as error:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail={"code": "review_forbidden"}
        ) from error
    except (ReviewConflict, StoredReviewConflict) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "review_conflict"}) from error
    return DecisionResponse(
        decision_id=result.decision_id,
        review_id=result.review_id,
        state=result.state,
        delivery_pending=result.delivery_pending,
    )
