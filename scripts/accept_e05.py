"""Real demo media ingest acceptance through probe/derivatives/scenes/catalog persistence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import and_, func, insert, select

import packages.persistence.schema as schema
from apps.services.media_ingest import MediaIngestService
from packages.artifacts import LocalObjectStore
from packages.contracts import ArtifactRef, RightsMetadata
from packages.persistence.database import create_database_engine
from packages.providers.media import FFmpegMediaProvider

DATABASE_URL = (
    "postgresql+psycopg://narratopro:replace-with-a-local-secret@127.0.0.1:5432/"
    "narratopro_e02_acceptance"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/Users/chinglam/Desktop/youzijuchang_demo.mp4"),
    )
    args = parser.parse_args()
    engine = create_database_engine(DATABASE_URL)
    project_id, run_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            insert(schema.project).values(id=project_id, name="E05 demo acceptance", state="active")
        )
        connection.execute(
            insert(schema.run).values(
                id=run_id,
                project_id=project_id,
                workflow_id=f"e05/{run_id}",
                state="running",
                automation_policy_snapshot={"level": "L1"},
                resource_profile_snapshot={"queue": "media"},
            )
        )
    profile_ref = ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": 1, "artifact_type": "ConfigArtifact"}
    )
    rights = RightsMetadata.model_validate(
        {
            "status": "unknown",
            "source": "user-provided-local-demo",
            "checked_at": datetime.now(UTC),
        }
    )
    store = LocalObjectStore(Path("artifacts/acceptance/e05_object_store"))
    service = MediaIngestService(
        engine=engine,
        object_store=store,
        provider=FFmpegMediaProvider(),
    )
    first = service.ingest(
        project_id=project_id,
        run_id=run_id,
        source_path=args.source,
        rights=rights,
        profile_ref=profile_ref,
        profile_version="demo-ingest-v1",
        trace_id="c" * 32,
    )
    second = service.ingest(
        project_id=project_id,
        run_id=run_id,
        source_path=args.source,
        rights=rights,
        profile_ref=profile_ref,
        profile_version="demo-ingest-v1",
        trace_id="c" * 32,
    )
    require(
        first.source == second.source and second.reused_source, "duplicate ingest was not reused"
    )
    require(
        first.proxy == second.proxy and first.audio == second.audio,
        "derivatives were not idempotent",
    )
    require(first.audio is not None, "demo audio stem is missing")
    blockers = rights.release_blockers(at=datetime.now(UTC), platform="douyin", territory="CN")
    require("rights_status:unknown" in blockers, "unknown rights did not block release")
    with engine.connect() as connection:
        scene_payload = connection.scalar(
            select(schema.artifact_version.c.payload_json).where(
                and_(
                    schema.artifact_version.c.artifact_id == first.scene_shot_catalog.artifact_id,
                    schema.artifact_version.c.version == 1,
                )
            )
        )
        plan_payload = connection.scalar(
            select(schema.artifact_version.c.payload_json).where(
                schema.artifact_version.c.artifact_id == first.frame_plan.artifact_id
            )
        )
        artifact_count = int(
            connection.scalar(
                select(func.count())
                .select_from(schema.artifact)
                .where(schema.artifact.c.project_id == project_id)
            )
            or 0
        )
    require(isinstance(scene_payload, dict) and scene_payload["segments"], "no shots detected")
    require(
        isinstance(plan_payload, dict)
        and plan_payload["samples"]
        and plan_payload["parameters"]["frame_assets"],
        "frame sampling assets are incomplete",
    )
    print(
        json.dumps(
            {
                "artifacts": artifact_count,
                "audio": True,
                "demo_bytes": args.source.stat().st_size,
                "frame_samples": len(plan_payload["samples"]),
                "idempotent": True,
                "release_blocked_unknown_rights": True,
                "shots": len(scene_payload["segments"]),
                "source_artifact": str(first.source.artifact_id),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
