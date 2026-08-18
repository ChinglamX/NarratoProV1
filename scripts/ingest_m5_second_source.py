"""Ingest the rights-restricted second source for M5 repeatability validation."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import insert, update

import packages.persistence.schema as schema
from apps.services.media_ingest import MediaIngestService
from packages.artifacts import LocalObjectStore
from packages.contracts import ActorRef, ArtifactRef
from packages.contracts.rights import RightsGrantRef, RightsMetadata, RightsStatus
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from packages.persistence.policy_repository import PublicationRepository
from packages.providers.media import FFmpegMediaProvider

DEFAULT_SOURCE = Path(
    "/Users/chinglam/Desktop/短剧素材/又子剧场热款视频-男频/5.山神印觉醒后满山风月皆归我/2.mp4"
)
TRACE_ID = "5f5e0ea7ab1e4d16a0c5202608180000"


def _ref_dict(reference: ArtifactRef | None) -> dict[str, object] | None:
    if reference is None:
        return None
    return {
        "artifact_id": str(reference.artifact_id),
        "version": reference.version,
        "artifact_type": reference.artifact_type,
        "checksum": str(reference.checksum) if reference.checksum else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/m5_second_source/ingest_manifest.json"),
    )
    args = parser.parse_args()
    source = args.source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    settings = get_settings()
    engine = create_database_engine(settings.database_url)
    store = LocalObjectStore(settings.object_store_root)
    repository = ArtifactRepository()
    policies = PublicationRepository()
    project_id = uuid4()
    run_id = uuid4()
    profile_ref = ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": 1, "artifact_type": "ConfigArtifact"}
    )
    actor = ActorRef.model_validate({"kind": "human", "id": "project-owner"})
    checked_at = datetime.now(UTC)

    with engine.begin() as connection:
        connection.execute(
            insert(schema.project).values(
                id=project_id,
                name="M5 repeatability — 山神印 episode 2",
                state="active",
            )
        )
        connection.execute(
            insert(schema.run).values(
                id=run_id,
                project_id=project_id,
                workflow_id=f"m5-second-source/{run_id}",
                state="running",
                automation_policy_snapshot={"level": "L1"},
                resource_profile_snapshot={"purpose": "m5-repeatability"},
            )
        )
        grant_ref = commit_contract_artifact(
            connection,
            repository,
            artifact_id=uuid4(),
            artifact_type="RightsGrant",
            payload={
                "source_path": str(source),
                "grant": "project-owner-confirmed-internal-processing-2026-08-18",
                "allowed": ["internal-analysis", "internal-editing", "internal-test-render"],
                "prohibited": ["public-release"],
                "source_note": "user states files are publicly accessible",
            },
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id=TRACE_ID,
            actor=actor,
            producer_module="m5-second-source-ingest",
            module_version="1",
            resource_profile_ref=profile_ref,
            rights_class="internal-only",
        )

    rights = RightsMetadata(
        status=RightsStatus.RESTRICTED,
        source=f"project-owner-provided-local-file:{source}",
        license="internal-processing-confirmation-2026-08-18",
        grant_ref=RightsGrantRef.model_validate(grant_ref.model_dump(mode="json")),
        platforms=frozenset({"internal-preview"}),
        modification=True,
        synchronization=True,
        restrictions=("no-public-release", "no-commercial-publication"),
        checked_at=checked_at,
    )
    service = MediaIngestService(
        engine=engine,
        object_store=store,
        provider=FFmpegMediaProvider(),
    )
    result = service.ingest(
        project_id=project_id,
        run_id=run_id,
        source_path=source,
        rights=rights,
        profile_ref=profile_ref,
        profile_version="m5-second-source-v1",
        trace_id=TRACE_ID,
    )
    with engine.begin() as connection:
        policies.record_asset_rights(
            connection,
            project_id=project_id,
            asset_ref=_ref_dict(result.source) or {},
            rights=rights,
        )
        connection.execute(
            update(schema.run).where(schema.run.c.id == run_id).values(state="succeeded")
        )

    payload = {
        "project_id": str(project_id),
        "run_id": str(run_id),
        "source_path": str(source),
        "rights": rights.model_dump(mode="json"),
        "rights_grant": _ref_dict(grant_ref),
        "artifacts": {
            "source": _ref_dict(result.source),
            "probe": _ref_dict(result.probe),
            "proxy": _ref_dict(result.proxy),
            "audio": _ref_dict(result.audio),
            "frame_plan": _ref_dict(result.frame_plan),
            "scene_shot_catalog": _ref_dict(result.scene_shot_catalog),
        },
        "reused_source": result.reused_source,
        "derivative_count": result.derivative_count,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
