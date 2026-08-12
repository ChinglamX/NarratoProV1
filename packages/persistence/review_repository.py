"""Transactional review decisions and durable Temporal signal outbox."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection, and_, func, insert, select, update
from sqlalchemy.exc import IntegrityError

import packages.persistence.schema as schema


class StoredReviewConflict(RuntimeError):
    pass


class StoredReviewForbidden(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StoredReviewDecision:
    decision_id: UUID
    review_id: UUID
    state: str
    delivery_pending: bool


@dataclass(frozen=True, slots=True)
class PendingSignal:
    event_id: UUID
    workflow_id: str
    payload: dict[str, Any]
    attempts: int


class ReviewRepository:
    def create_request(
        self,
        connection: Connection,
        *,
        review_id: UUID,
        project_id: UUID,
        workflow_id: str,
        gate: str,
        target_ref: dict[str, Any],
        policy_snapshot: dict[str, Any],
        deadline: datetime | None = None,
    ) -> None:
        connection.execute(
            insert(schema.review_request).values(
                id=review_id,
                project_id=project_id,
                workflow_id=workflow_id,
                gate=gate,
                target_ref=target_ref,
                state="awaiting_review",
                policy_snapshot=policy_snapshot,
                deadline=deadline,
            )
        )

    def decide(
        self,
        connection: Connection,
        *,
        review_id: UUID,
        expected_target_version: int,
        decision: str,
        reviewer_snapshot: dict[str, Any],
        reasons: list[dict[str, Any]],
        trace_id: str,
    ) -> StoredReviewDecision:
        row = (
            connection.execute(
                select(schema.review_request)
                .where(schema.review_request.c.id == review_id)
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if row is None:
            raise StoredReviewConflict("review does not exist")
        roles = set(reviewer_snapshot.get("roles", []))
        if row["gate"] == "release":
            if "release_approver" not in roles or reviewer_snapshot.get("service_account"):
                raise StoredReviewForbidden("human release_approver is required")
        elif "reviewer" not in roles:
            raise StoredReviewForbidden("reviewer role is required")
        actual_version = int(row["target_ref"]["version"])
        if row["state"] != "awaiting_review" or expected_target_version != actual_version:
            raise StoredReviewConflict("review target is stale or already decided")
        policy = row["policy_snapshot"]
        if row["gate"] == "story" and decision == "approve":
            package = policy.get("story_review_package", {})
            if package.get("incomplete") or package.get("blocker_codes"):
                raise StoredReviewConflict("blocked or incomplete story cannot be approved")
        decision_id = uuid4()
        try:
            connection.execute(
                insert(schema.review_decision).values(
                    id=decision_id,
                    request_id=review_id,
                    decision=decision,
                    reviewer_json=reviewer_snapshot,
                    reasons=reasons,
                )
            )
            updated = connection.execute(
                update(schema.review_request)
                .where(
                    and_(
                        schema.review_request.c.id == review_id,
                        schema.review_request.c.state == "awaiting_review",
                    )
                )
                .values(state="decided")
            )
            if updated.rowcount != 1:
                raise StoredReviewConflict("review was already decided")
            if row["gate"] == "story" and decision == "approve":
                connection.execute(
                    select(func.pg_advisory_xact_lock(row["project_id"].int & (2**63 - 1)))
                )
                publication = connection.execute(
                    select(schema.publication_pointer)
                    .where(
                        and_(
                            schema.publication_pointer.c.project_id == row["project_id"],
                            schema.publication_pointer.c.registry_type == "approved_story",
                        )
                    )
                    .with_for_update()
                ).first()
                values = {
                    "registry_id": UUID(str(row["target_ref"]["artifact_id"])),
                    "version": actual_version,
                }
                if publication is None:
                    connection.execute(
                        insert(schema.publication_pointer).values(
                            project_id=row["project_id"],
                            registry_type="approved_story",
                            **values,
                        )
                    )
                else:
                    connection.execute(
                        update(schema.publication_pointer)
                        .where(
                            and_(
                                schema.publication_pointer.c.project_id == row["project_id"],
                                schema.publication_pointer.c.registry_type == "approved_story",
                                schema.publication_pointer.c.row_version == publication.row_version,
                            )
                        )
                        .values(
                            **values,
                            row_version=schema.publication_pointer.c.row_version + 1,
                        )
                    )
            connection.execute(
                insert(schema.outbox_event).values(
                    id=uuid4(),
                    aggregate_id=str(review_id),
                    event_type="review.decision.signal",
                    payload_json={
                        "workflow_id": row["workflow_id"],
                        "review_id": str(review_id),
                        "target_version": actual_version,
                        "decision": decision,
                    },
                    trace_id=trace_id,
                )
            )
        except IntegrityError as error:
            raise StoredReviewConflict("review was already decided") from error
        return StoredReviewDecision(decision_id, review_id, "decided", True)

    def approved_story(self, connection: Connection, *, project_id: UUID) -> dict[str, Any] | None:
        row = connection.execute(
            select(schema.publication_pointer).where(
                and_(
                    schema.publication_pointer.c.project_id == project_id,
                    schema.publication_pointer.c.registry_type == "approved_story",
                )
            )
        ).first()
        if row is None:
            return None
        return {
            "artifact_id": row.registry_id,
            "version": int(row.version),
            "artifact_type": "StoryGraph",
        }

    def pending_signals(self, connection: Connection, *, limit: int = 100) -> list[PendingSignal]:
        rows = connection.execute(
            select(schema.outbox_event)
            .where(
                and_(
                    schema.outbox_event.c.event_type == "review.decision.signal",
                    schema.outbox_event.c.published_at.is_(None),
                )
            )
            .order_by(schema.outbox_event.c.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).mappings()
        return [
            PendingSignal(
                event_id=row["id"],
                workflow_id=str(row["payload_json"]["workflow_id"]),
                payload=dict(row["payload_json"]),
                attempts=int(row["attempts"]),
            )
            for row in rows
        ]

    def mark_signal_delivered(self, connection: Connection, event_id: UUID) -> None:
        connection.execute(
            update(schema.outbox_event)
            .where(schema.outbox_event.c.id == event_id)
            .values(published_at=datetime.now(UTC))
        )

    def mark_signal_attempt_failed(self, connection: Connection, event_id: UUID) -> None:
        connection.execute(
            update(schema.outbox_event)
            .where(schema.outbox_event.c.id == event_id)
            .values(attempts=schema.outbox_event.c.attempts + 1)
        )
