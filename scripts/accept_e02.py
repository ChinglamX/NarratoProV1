"""Real PostgreSQL acceptance for E02 artifact and persistence invariants."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select

from packages.artifacts import LocalObjectStore
from packages.contracts import ArtifactDependency, ArtifactEnvelope, ArtifactRef, RightsMetadata
from packages.persistence import (
    ArtifactRepository,
    BlobRepository,
    CommandRepository,
    DependencyCycle,
    IdempotencyConflict,
    PublicationConflict,
    PublicationRepository,
    VersionConflict,
    create_database_engine,
    schema,
)


def reference(artifact_id: UUID, version: int, artifact_type: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": artifact_id, "version": version, "artifact_type": artifact_type}
    )


def envelope(
    *,
    artifact_id: UUID,
    artifact_type: str,
    version: int,
    project_id: UUID,
    run_id: UUID,
    digest_character: str,
    inputs: tuple[ArtifactRef, ...] = (),
) -> ArtifactEnvelope:
    return ArtifactEnvelope.model_validate(
        {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "schema_version": "1.0.0",
            "version": version,
            "project_id": project_id,
            "run_id": run_id,
            "state": "committed",
            "created_at": datetime.now(UTC),
            "created_by": {"kind": "system", "id": "e02-acceptance"},
            "inputs": inputs,
            "producer": {
                "module": "e02-acceptance",
                "module_version": "1.0.0",
                "resource_profile_ref": {
                    "artifact_id": uuid4(),
                    "version": 1,
                    "artifact_type": "ResourceProfile",
                },
            },
            "checksum": "sha256:" + digest_character * 64,
            "rights_class": "acceptance-only",
            "trace_id": digest_character * 32,
            "payload": {"acceptance_version": version},
        }
    )


def accept(database_url: str) -> dict[str, int | bool]:
    engine = create_database_engine(database_url)
    repository = ArtifactRepository()
    project_id, run_id = uuid4(), uuid4()
    root_id, middle_id, leaf_id = uuid4(), uuid4(), uuid4()
    with TemporaryDirectory(prefix="narratopro-e02-") as directory, engine.begin() as connection:
        connection.execute(
            insert(schema.project).values(id=project_id, name="E02 acceptance", state="active")
        )
        publication_repository = PublicationRepository()
        policy_id = uuid4()
        publication_repository.publish_automation_policy(
            connection,
            project_id=project_id,
            policy_id=policy_id,
            version=1,
            scope={"project_id": str(project_id)},
            policy={"level": "L1", "fallback": "fail_closed"},
            expected_pointer_version=0,
        )
        try:
            publication_repository.publish_automation_policy(
                connection,
                project_id=project_id,
                policy_id=policy_id,
                version=2,
                scope={"project_id": str(project_id)},
                policy={"level": "L2", "fallback": "fail_closed"},
                expected_pointer_version=0,
            )
        except PublicationConflict:
            publication_conflict_rejected = True
        else:
            raise RuntimeError("stale policy publication pointer was accepted")
        config_ref = publication_repository.create_effective_config_snapshot(
            connection,
            project_id=project_id,
            schema_version="1.0.0",
            resolved_config={"automation": "L1", "genre": "acceptance"},
        )
        unknown_rights = RightsMetadata.model_validate(
            {"status": "unknown", "checked_at": datetime.now(UTC)}
        )
        publication_repository.record_asset_rights(
            connection,
            project_id=project_id,
            asset_ref={"artifact_id": str(root_id), "version": 1},
            rights=unknown_rights,
        )
        rights_blocked = bool(
            unknown_rights.release_blockers(at=datetime.now(UTC), platform="douyin", territory="CN")
        )
        command_repository = CommandRepository()
        command_id = uuid4()
        first_command = command_repository.register(
            connection,
            command_id=command_id,
            idempotency_key="e02-acceptance-command",
            command_type="project.create",
            project_id=project_id,
            request={"name": "E02 acceptance"},
            request_checksum="sha256:" + "a" * 64,
        )
        replayed_command = command_repository.register(
            connection,
            command_id=uuid4(),
            idempotency_key="e02-acceptance-command",
            command_type="project.create",
            project_id=project_id,
            request={"name": "E02 acceptance"},
            request_checksum="sha256:" + "a" * 64,
        )
        if replayed_command.command_id != first_command.command_id:
            raise RuntimeError("idempotent replay returned a different command")
        try:
            command_repository.register(
                connection,
                command_id=uuid4(),
                idempotency_key="e02-acceptance-command",
                command_type="project.create",
                project_id=project_id,
                request={"name": "different"},
                request_checksum="sha256:" + "b" * 64,
            )
        except IdempotencyConflict:
            idempotency_conflict_rejected = True
        else:
            raise AssertionError("idempotency key accepted a different request")
        connection.execute(
            insert(schema.run).values(
                id=run_id,
                project_id=project_id,
                workflow_id=f"e02-{run_id}",
                state="running",
                automation_policy_snapshot={"level": "L1"},
                resource_profile_snapshot={"profile": "acceptance"},
            )
        )
        for artifact_id, artifact_type in (
            (root_id, "FactSet"),
            (middle_id, "StoryGraph"),
            (leaf_id, "CreativeBrief"),
        ):
            repository.reserve(
                connection,
                artifact_id=artifact_id,
                project_id=project_id,
                artifact_type=artifact_type,
            )
        object_store = LocalObjectStore(Path(directory) / "object-store")
        staged = object_store.stage(run_id, "acceptance-blob", BytesIO(b"e02-blob"))
        blob_repository = BlobRepository()
        registered = blob_repository.register_staged(
            connection,
            staged,
            content_type="application/octet-stream",
        )
        committed_blob = blob_repository.commit(connection, object_store, registered)
        if object_store.open(committed_blob.metadata.uri).read() != b"e02-blob":
            raise RuntimeError("committed blob content mismatch")
        root_v1 = envelope(
            artifact_id=root_id,
            artifact_type="FactSet",
            version=1,
            project_id=project_id,
            run_id=run_id,
            digest_character="1",
        )
        repository.commit_version(connection, root_v1, expected_latest_version=0)
        middle_v1 = envelope(
            artifact_id=middle_id,
            artifact_type="StoryGraph",
            version=1,
            project_id=project_id,
            run_id=run_id,
            digest_character="2",
            inputs=(root_v1.as_ref(),),
        )
        repository.commit_version(connection, middle_v1, expected_latest_version=0)
        leaf_v1 = envelope(
            artifact_id=leaf_id,
            artifact_type="CreativeBrief",
            version=1,
            project_id=project_id,
            run_id=run_id,
            digest_character="3",
            inputs=(middle_v1.as_ref(),),
        )
        repository.commit_version(connection, leaf_v1, expected_latest_version=0)
        try:
            repository.add_dependency(
                connection,
                ArtifactDependency.model_validate(
                    {
                        "upstream": leaf_v1.as_ref(),
                        "downstream": root_v1.as_ref(),
                        "dependency_type": "semantic",
                        "invalidation_rule": "cycle-fixture",
                    }
                ),
            )
        except DependencyCycle:
            cycle_rejected = True
        else:
            raise AssertionError("dependency cycle was accepted")
        plan = repository.invalidate(
            connection,
            project_id=project_id,
            root=root_v1.as_ref(),
            change_set={"fact": "corrected"},
            trace_id="4" * 32,
        )
        if {item.artifact_id for item in plan.affected} != {middle_id, leaf_id}:
            raise RuntimeError("dependency invalidation closure mismatch")

    def concurrent_commit(character: str) -> bool:
        candidate = envelope(
            artifact_id=root_id,
            artifact_type="FactSet",
            version=2,
            project_id=project_id,
            run_id=run_id,
            digest_character=character,
        )
        try:
            with engine.begin() as connection:
                repository.commit_version(connection, candidate, expected_latest_version=1)
        except VersionConflict:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(concurrent_commit, ("5", "6")))
    if results.count(True) != 1 or results.count(False) != 1:
        raise RuntimeError("concurrent CAS did not produce exactly one winner")

    with engine.connect() as connection:
        outbox_count = int(
            connection.scalar(select(func.count()).select_from(schema.outbox_event)) or 0
        )
        version_count = int(
            connection.scalar(select(func.count()).select_from(schema.artifact_version)) or 0
        )
        pointer_version = int(
            connection.scalar(
                select(schema.active_pointer.c.version).where(
                    schema.active_pointer.c.artifact_id == root_id
                )
            )
            or 0
        )
    engine.dispose()
    return {
        "cycle_rejected": cycle_rejected,
        "concurrent_winners": results.count(True),
        "artifact_versions": version_count,
        "outbox_events": outbox_count,
        "root_active_version": pointer_version,
        "invalidation_affected": len(plan.affected),
        "blob_committed": committed_blob.state == "committed",
        "idempotency_conflict_rejected": idempotency_conflict_rejected,
        "publication_conflict_rejected": publication_conflict_rejected,
        "effective_config_created": config_ref.version == 1,
        "unknown_rights_blocked": rights_blocked,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    print(json.dumps(accept(args.database_url), sort_keys=True))


if __name__ == "__main__":
    main()
