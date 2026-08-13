"""DB-backed TimelineRepository tests.

These tests exercise real SQL (version allocation, pointer CAS, approved
intent lookup) and are skipped when no migrated PostgreSQL database is
reachable (CI has no Postgres service; run locally with
``NARRATOPRO_DATABASE_URL`` pointing at a migrated test database).
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import OperationalError

import packages.persistence.schema as schema
from packages.persistence.database import create_database_engine, transaction
from packages.persistence.timeline_repository import (
    TimelineRepository,
    TimelineSnapshot,
    TimelineStorageConflict,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("NARRATOPRO_DATABASE_URL"),
    reason="NARRATOPRO_DATABASE_URL not set",
)


@pytest.fixture(scope="module")
def engine():
    engine = create_database_engine(os.environ["NARRATOPRO_DATABASE_URL"])
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM artifact.active_pointer LIMIT 1"))
    except OperationalError as error:
        pytest.skip(f"database unreachable or not migrated: {error}")
    return engine


def _seed_timeline(
    connection: object,
    *,
    timeline_id: UUID,
    versions: list[int],
) -> tuple[UUID, UUID]:
    project_id = uuid4()
    run_id = uuid4()
    connection.execute(insert(schema.project).values(id=project_id, name="db-test", state="active"))
    connection.execute(
        insert(schema.run).values(
            id=run_id,
            project_id=project_id,
            workflow_id=f"db-test-{uuid4()}",
            state="completed",
            automation_policy_snapshot={},
            resource_profile_snapshot={},
        )
    )
    connection.execute(
        insert(schema.artifact).values(
            id=timeline_id, project_id=project_id, artifact_type="MasterTimeline"
        )
    )
    for version in versions:
        connection.execute(
            insert(schema.artifact_version).values(
                artifact_id=timeline_id,
                version=version,
                schema_version="1.0.0",
                run_id=run_id,
                variant_id=None,
                state="committed",
                payload_json={"timeline_id": str(timeline_id), "version": version},
                checksum=f"sha256:{version:064x}",
                producer_json={"kind": "test"},
                rights_class="internal",
                trace_id="0" * 32,
            )
        )
    connection.execute(
        insert(schema.active_pointer).values(artifact_id=timeline_id, version=max(versions))
    )
    return project_id, run_id


def _snapshot(timeline_id: UUID, version: int, run_id: UUID) -> TimelineSnapshot:
    return TimelineSnapshot(
        version=version,
        payload={"timeline_id": str(timeline_id), "version": version},
        schema_version="1.0.0",
        run_id=run_id,
        variant_id=None,
        producer={"kind": "test"},
        rights_class="internal",
    )


class TestCommitVersionAllocation:
    def test_commit_after_undo_appends_new_version(self, engine) -> None:
        """Undo to v2 then edit must create v4, not collide with v3 (PK)."""
        timeline_id = uuid4()
        repository = TimelineRepository()
        with transaction(engine) as connection:
            _project_id, run_id = _seed_timeline(
                connection, timeline_id=timeline_id, versions=[1, 2, 3]
            )
            repository.set_active_version(
                connection,
                artifact_id=timeline_id,
                target_version=2,
                expected_version=3,
                trace_id="0" * 32,
                reason="test:undo",
            )
            version = repository.commit(
                connection,
                artifact_id=timeline_id,
                current=_snapshot(timeline_id, 2, run_id),
                payload={"timeline_id": str(timeline_id), "version": 4},
                checksum="sha256:" + "a" * 64,
                patch_id=uuid4(),
                rebased=True,
                trace_id="0" * 32,
            )
            assert version == 4
            assert repository.get_active_version(connection, artifact_id=timeline_id) == 4
            versions = repository.list_versions(connection, artifact_id=timeline_id)
            assert {v.version for v in versions} == {1, 2, 3, 4}


class TestActivePointerCas:
    def test_set_active_version_missing_target_raises(self, engine) -> None:
        timeline_id = uuid4()
        repository = TimelineRepository()
        with transaction(engine) as connection:
            _seed_timeline(connection, timeline_id=timeline_id, versions=[1])
            with pytest.raises(TimelineStorageConflict, match="does not exist"):
                repository.set_active_version(
                    connection,
                    artifact_id=timeline_id,
                    target_version=99,
                    expected_version=1,
                    trace_id="0" * 32,
                    reason="test",
                )

    def test_set_active_version_stale_expected_raises(self, engine) -> None:
        timeline_id = uuid4()
        repository = TimelineRepository()
        with transaction(engine) as connection:
            _seed_timeline(connection, timeline_id=timeline_id, versions=[1, 2])
            with pytest.raises(TimelineStorageConflict, match="CAS failed"):
                repository.set_active_version(
                    connection,
                    artifact_id=timeline_id,
                    target_version=2,
                    expected_version=99,
                    trace_id="0" * 32,
                    reason="test",
                )


class TestApprovedIntent:
    def test_approved_intent_version_roundtrip(self, engine) -> None:
        timeline_id = uuid4()
        repository = TimelineRepository()
        with transaction(engine) as connection:
            project_id, _run_id = _seed_timeline(
                connection, timeline_id=timeline_id, versions=[1, 2]
            )
            assert repository.approved_intent_version(connection, artifact_id=timeline_id) is None
            connection.execute(
                insert(schema.publication_pointer).values(
                    project_id=project_id,
                    registry_type="approved_timeline_intent",
                    registry_id=timeline_id,
                    version=2,
                    row_version=1,
                )
            )
            assert repository.approved_intent_version(connection, artifact_id=timeline_id) == 2
