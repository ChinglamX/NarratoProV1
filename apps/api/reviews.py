"""Review command API; decisions are committed before signal delivery."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from packages.contracts import (
    ReleaseReviewPackage,
    StoryReviewPackage,
    StrategyGateSelection,
    StrategyReviewPackage,
    TimelineReviewPackage,
)
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
    strategy_selection: StrategyGateSelection | None = None


class DecisionResponse(BaseModel):
    decision_id: UUID
    review_id: UUID
    state: str
    delivery_pending: bool


class StoryReviewRequestBody(BaseModel):
    review_id: UUID
    project_id: UUID
    workflow_id: str = Field(min_length=1, max_length=255)
    package: StoryReviewPackage


class StrategyReviewRequestBody(BaseModel):
    review_id: UUID
    project_id: UUID
    workflow_id: str = Field(min_length=1, max_length=255)
    package: StrategyReviewPackage


class ReleaseReviewRequestBody(BaseModel):
    review_id: UUID
    project_id: UUID
    workflow_id: str = Field(min_length=1, max_length=255)
    package: ReleaseReviewPackage


class TimelineReviewRequestBody(BaseModel):
    review_id: UUID
    project_id: UUID
    workflow_id: str = Field(min_length=1, max_length=255)
    package: TimelineReviewPackage


class TimelineReviewResponse(BaseModel):
    review_id: UUID
    project_id: UUID
    state: str
    target_version: int
    package: TimelineReviewPackage


@router.get("/timeline/{review_id}", response_model=TimelineReviewResponse)
def get_timeline_review(review_id: UUID, request: Request) -> TimelineReviewResponse:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with engine.connect() as connection:
        snapshot = repository.snapshot(connection, review_id=review_id)
    if snapshot is None or snapshot.gate != "timeline":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "timeline_review_not_found"})
    package = snapshot.policy_snapshot.get("timeline_review_package")
    if not isinstance(package, dict):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "timeline_review_package_missing"}
        )
    return TimelineReviewResponse(
        review_id=snapshot.review_id,
        project_id=snapshot.project_id,
        state=snapshot.state,
        target_version=int(snapshot.target_ref["version"]),
        package=TimelineReviewPackage.model_validate(package),
    )


@router.post("/timeline", status_code=status.HTTP_201_CREATED)
def create_timeline_review(body: TimelineReviewRequestBody, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with transaction(engine) as connection:
        repository.create_request(
            connection,
            review_id=body.review_id,
            project_id=body.project_id,
            workflow_id=body.workflow_id,
            gate="timeline",
            target_ref=body.package.master_timeline_ref.model_dump(mode="json"),
            policy_snapshot={
                "automation_level": "L1",
                "timeline_review_package": body.package.model_dump(mode="json"),
            },
        )
    return {"review_id": body.review_id, "state": "awaiting_review", "gate": "timeline"}


@router.get("/timeline/approved/{project_id}")
def get_approved_timeline(project_id: UUID, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with engine.connect() as connection:
        reference = repository.publication_ref(
            connection,
            project_id=project_id,
            registry_type="approved_timeline_intent",
            artifact_type="MasterTimeline",
        )
    if reference is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "timeline_not_approved"})
    return {"approved_timeline_intent_ref": reference}


@router.post("/story", status_code=status.HTTP_201_CREATED)
def create_story_review(body: StoryReviewRequestBody, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with transaction(engine) as connection:
        repository.create_request(
            connection,
            review_id=body.review_id,
            project_id=body.project_id,
            workflow_id=body.workflow_id,
            gate="story",
            target_ref=body.package.story_graph_ref.model_dump(mode="json"),
            policy_snapshot={
                "automation_level": "L1",
                "story_review_package": body.package.model_dump(mode="json"),
            },
        )
    return {"review_id": body.review_id, "state": "awaiting_review", "gate": "story"}


@router.get("/story/approved/{project_id}")
def get_approved_story(project_id: UUID, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with engine.connect() as connection:
        reference = repository.approved_story(connection, project_id=project_id)
    if reference is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "story_not_approved"})
    return {"approved_story_ref": reference}


@router.post("/strategy", status_code=status.HTTP_201_CREATED)
def create_strategy_review(body: StrategyReviewRequestBody, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with transaction(engine) as connection:
        repository.create_request(
            connection,
            review_id=body.review_id,
            project_id=body.project_id,
            workflow_id=body.workflow_id,
            gate="strategy",
            target_ref=body.package.comparison_ref.model_dump(mode="json"),
            policy_snapshot={
                "automation_level": "L1",
                "strategy_review_package": body.package.model_dump(mode="json"),
            },
        )
    return {"review_id": body.review_id, "state": "awaiting_review", "gate": "strategy"}


@router.get("/strategy/approved/{project_id}")
def get_approved_strategy(project_id: UUID, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with engine.connect() as connection:
        brief = repository.approved_strategy_ref(
            connection, project_id=project_id, registry_type="approved_creative_brief"
        )
        variants = repository.approved_strategy_ref(
            connection, project_id=project_id, registry_type="approved_variant_plan"
        )
    if brief is None or variants is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "strategy_not_approved"})
    return {"approved_creative_brief_ref": brief, "approved_variant_plan_ref": variants}


@router.post("/release", status_code=status.HTTP_201_CREATED)
def create_release_review(body: ReleaseReviewRequestBody, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with transaction(engine) as connection:
        repository.create_request(
            connection,
            review_id=body.review_id,
            project_id=body.project_id,
            workflow_id=body.workflow_id,
            gate="release",
            target_ref=body.package.final_candidate_ref.model_dump(mode="json"),
            policy_snapshot={
                "automation_level": "L1",
                "release_review_package": body.package.model_dump(mode="json"),
            },
        )
    return {"review_id": body.review_id, "state": "awaiting_review", "gate": "release"}


@router.get("/release/approved/{project_id}")
def get_released_candidate(project_id: UUID, request: Request) -> dict[str, Any]:
    engine: Engine = request.app.state.database_engine
    repository: ReviewRepository = request.app.state.review_repository
    with engine.connect() as connection:
        reference = repository.publication_ref(
            connection,
            project_id=project_id,
            registry_type="released_candidate",
            artifact_type="FinalCandidate",
        )
    if reference is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "candidate_not_released"})
    return {"released_candidate_ref": reference}


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
                strategy_selection=(
                    body.strategy_selection.model_dump(mode="json")
                    if body.strategy_selection is not None
                    else None
                ),
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
