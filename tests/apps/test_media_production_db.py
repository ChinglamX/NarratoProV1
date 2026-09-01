"""E10 media production persistence integration tests (local PostgreSQL).

Mirrors tests/persistence/test_timeline_repository_db.py: skipped in CI
without a migrated database; run locally against narratopro_test-style DB.
"""

import os
from uuid import uuid4

import pytest

from apps.services.media_production import MediaProductionService
from packages.artifacts import LocalObjectStore
from packages.contracts import ActorRef, ArtifactRef
from packages.contracts.media_production import AudioRole, MixPlan, MixStem
from packages.foundation.settings import get_settings
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine

pytestmark = pytest.mark.skipif(
    not os.environ.get("NARRATOPRO_DATABASE_URL"),
    reason="NARRATOPRO_DATABASE_URL not set",
)


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _setup_run(engine, project_id) -> tuple:
    from uuid import uuid4 as _u

    run_id = _u()
    with engine.begin() as connection:
        connection.execute(
            __import__("sqlalchemy").text(
                "insert into core.run (id, project_id, workflow_id, state, "
                "automation_policy_snapshot, resource_profile_snapshot) "
                "values (:i,:p,:w,'running','{}','{}')"
            ),
            {"i": run_id, "p": project_id, "w": f"e10-test/{run_id}"},
        )
    return run_id


def test_persist_mix_plan_and_ass_artifact() -> None:
    engine = create_database_engine(get_settings().database_url)
    with engine.connect() as connection:
        project_id = connection.execute(
            __import__("sqlalchemy").text("select id from core.project limit 1")
        ).scalar()
    run_id = _setup_run(engine, project_id)
    service = MediaProductionService(
        artifacts=ArtifactRepository(), store=LocalObjectStore(get_settings().object_store_root)
    )
    actor = ActorRef.model_validate({"kind": "human", "id": "e10-db-test"})
    rp_ref = _ref("ResourceProfile")

    mix = MixPlan(
        conformed_timeline_ref=_ref("MasterTimeline"),
        stems=(
            MixStem(
                role=AudioRole.NARRATION,
                source_ref=_ref("VoiceAsset"),
                timeline_range={
                    "start": {"value": 0, "rate_num": 1_000_000},
                    "duration": {"value": 4_000_000, "rate_num": 1_000_000},
                },
            ),
        ),
        target_loudness_lufs=-14.0,
        true_peak_ceiling_dbtp=-1.0,
        measurement_profile_ref=_ref("ConfigArtifact"),
    )
    with engine.begin() as connection:
        mix_ref = service.persist_mix_plan(
            connection,
            mix_plan=mix,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id="f" * 32,
            actor=actor,
            resource_profile_ref=rp_ref,
            inputs=(),
            rights_class="internal-planning",
        )
        profile_ref = commit_contract_artifact(
            connection,
            ArtifactRepository(),
            artifact_id=uuid4(),
            artifact_type="ConfigArtifact",
            payload={"profile": "subtitle-default"},
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id="f" * 32,
            actor=actor,
            producer_module="e10-test",
            module_version="1",
            resource_profile_ref=rp_ref,
            rights_class="internal-planning",
        )
        from packages.contracts.media_production import SubtitleCue, SubtitleCueSet

        cue_set = SubtitleCueSet(
            alignment_ref=_ref("AlignmentArtifact"),
            cues=(
                SubtitleCue(
                    cue_id=uuid4(),
                    timeline_range={
                        "start": {"value": 0, "rate_num": 1_000_000},
                        "duration": {"value": 4_000_000, "rate_num": 1_000_000},
                    },
                    text=f"字幕{uuid4().hex[:6]}",
                    style_ref="primary",
                    safe_area={"y": 0.8, "height": 0.14},
                ),
            ),
            style_profile_ref=profile_ref,
        )
        cue_set_ref = commit_contract_artifact(
            connection,
            ArtifactRepository(),
            artifact_id=uuid4(),
            artifact_type="SubtitleCueSet",
            payload=cue_set,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id="f" * 32,
            actor=actor,
            producer_module="e10-test",
            module_version="1",
            resource_profile_ref=rp_ref,
            rights_class="internal-planning",
        )
        ass_ref = service.persist_ass_artifact(
            connection,
            ass_content=f"[Script Info]\nScriptType: v4.00+\n; {uuid4()}\n",
            subtitle_cue_set_ref=cue_set_ref,
            libass_profile_ref=profile_ref,
            project_id=project_id,
            run_id=run_id,
            variant_id=None,
            trace_id="f" * 32,
            actor=actor,
            resource_profile_ref=rp_ref,
            rights_class="internal-planning",
        )
    assert mix_ref.artifact_type == "MixPlan"
    assert ass_ref.artifact_type == "ASSArtifact"
    with engine.connect() as connection:
        row = connection.execute(
            __import__("sqlalchemy").text(
                "select av.blob_id is not null as has_blob from artifact.artifact_version av "
                "where av.artifact_id = :id"
            ),
            {"id": ass_ref.artifact_id},
        ).first()
    assert row is not None and row.has_blob
