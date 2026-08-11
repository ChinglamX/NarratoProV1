"""Real PostgreSQL/API acceptance for E03 command, review and correction semantics."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import insert, select

import packages.persistence.schema as schema
from apps.api.main import create_app
from packages.control.reviews import ReviewGate
from packages.persistence.database import create_database_engine

DATABASE_URL = (
    "postgresql+psycopg://narratopro:replace-with-a-local-secret@127.0.0.1:5432/"
    "narratopro_e02_acceptance"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    engine = create_database_engine(DATABASE_URL)
    app = create_app()
    app.state.database_engine.dispose()
    app.state.database_engine = engine
    client = TestClient(app)
    key = str(uuid4())

    project_response = client.post(
        "/v1/projects", json={"name": "E03 acceptance"}, headers={"Idempotency-Key": key}
    )
    require(project_response.status_code == 201, "project command failed")
    project_body = project_response.json()
    repeated = client.post(
        "/v1/projects", json={"name": "E03 acceptance"}, headers={"Idempotency-Key": key}
    )
    require(repeated.json() == project_body, "idempotent replay changed response")
    conflict = client.post(
        "/v1/projects", json={"name": "different"}, headers={"Idempotency-Key": key}
    )
    require(conflict.status_code == 409, "idempotency conflict was not rejected")
    project_id = UUID(project_body["resource_id"])

    run_response = client.post(
        f"/v1/projects/{project_id}/runs",
        json={"automation_policy": {"level": "L1"}, "resource_profile": {"queue": "cpu"}},
        headers={"Idempotency-Key": str(uuid4()), "X-Trace-Id": "a" * 32},
    )
    require(run_response.status_code == 202, "run command failed")
    run_id = UUID(run_response.json()["resource_id"])

    artifact_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(schema.artifact).values(
                id=artifact_id, project_id=project_id, artifact_type="StoryGraph"
            )
        )
        connection.execute(
            insert(schema.artifact_version).values(
                artifact_id=artifact_id,
                version=1,
                schema_version="1.0.0",
                run_id=run_id,
                state="committed",
                payload_json={"story": {"title": "old"}},
                checksum="sha256:" + "1" * 64,
                producer_json={"kind": "acceptance"},
                rights_class="internal",
                trace_id="a" * 32,
            )
        )
        connection.execute(insert(schema.active_pointer).values(artifact_id=artifact_id, version=1))

    patch = {
        "project_id": str(project_id),
        "run_id": str(run_id),
        "base_version": 1,
        "operations": [{"operation": "replace", "path": ["story", "title"], "value": "new"}],
        "reason": "acceptance correction",
    }
    preview = client.post(f"/v1/artifacts/{artifact_id}/patches:preview", json=patch)
    require(
        preview.status_code == 200 and preview.json()["result"]["story"]["title"] == "new",
        "correction preview failed",
    )
    applied = client.post(
        f"/v1/artifacts/{artifact_id}/patches",
        json=patch,
        headers={"X-Actor-Id": "editor", "X-Actor-Roles": "editor"},
    )
    require(
        applied.status_code == 201 and applied.json()["version"] == 2,
        "correction apply failed",
    )
    stale = client.post(
        f"/v1/artifacts/{artifact_id}/patches",
        json=patch,
        headers={"X-Actor-Id": "editor", "X-Actor-Roles": "editor"},
    )
    require(stale.status_code == 409, "stale correction was not rejected")

    review_id = uuid4()
    release_review_id = uuid4()
    with engine.begin() as connection:
        repository = app.state.review_repository
        for candidate_id, gate in (
            (review_id, ReviewGate.STORY),
            (release_review_id, ReviewGate.RELEASE),
        ):
            repository.create_request(
                connection,
                review_id=candidate_id,
                project_id=project_id,
                workflow_id=f"workflow/{candidate_id}",
                gate=gate.value,
                target_ref={"artifact_id": str(artifact_id), "version": 2},
                policy_snapshot={"level": "L1"},
            )
    decision = {"expected_target_version": 2, "decision": "approve", "reasons": []}
    approved = client.post(
        f"/v1/reviews/{review_id}/decision",
        json=decision,
        headers={"X-Actor-Id": "reviewer", "X-Actor-Roles": "reviewer"},
    )
    require(
        approved.status_code == 202 and approved.json()["delivery_pending"],
        "review decision was not durably accepted",
    )
    require(
        client.post(
            f"/v1/reviews/{review_id}/decision",
            json=decision,
            headers={"X-Actor-Id": "reviewer", "X-Actor-Roles": "reviewer"},
        ).status_code
        == 409,
        "duplicate review decision was not rejected",
    )
    forbidden = client.post(
        f"/v1/reviews/{release_review_id}/decision",
        json=decision,
        headers={"X-Actor-Id": "reviewer", "X-Actor-Roles": "reviewer"},
    )
    require(forbidden.status_code == 403, "release RBAC did not fail closed")
    release = client.post(
        f"/v1/reviews/{release_review_id}/decision",
        json=decision,
        headers={"X-Actor-Id": "human", "X-Actor-Roles": "release_approver"},
    )
    require(release.status_code == 202, "human release approver was rejected")

    with engine.connect() as connection:
        start_events = connection.scalar(
            select(schema.outbox_event.c.id).where(
                schema.outbox_event.c.aggregate_id == str(run_id)
            )
        )
        corrected = connection.scalar(
            select(schema.active_pointer.c.version).where(
                schema.active_pointer.c.artifact_id == artifact_id
            )
        )
    require(start_events is not None and corrected == 2, "database state reconciliation failed")
    print(
        json.dumps(
            {
                "command_idempotency": True,
                "correction_cas": True,
                "outbox_start": True,
                "release_rbac": True,
                "review_first_wins": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
