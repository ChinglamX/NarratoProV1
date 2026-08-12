from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import ArtifactRef
from packages.contracts.render_release import (
    OfflineQualityReview,
    ReleaseRecord,
    ReleaseRightsManifest,
    RenderExecutionReport,
    RightsManifestEntry,
    TechnicalCheck,
    TechnicalQCReport,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def cleared_rights() -> dict[str, object]:
    return {
        "status": "cleared",
        "source": "owner",
        "license": "commercial",
        "grant_ref": ref("RightsGrant").model_dump(mode="json"),
        "territories": ["CN"],
        "platforms": ["douyin"],
        "commercial_use": True,
        "modification": True,
        "synchronization": True,
        "checked_at": datetime.now(UTC),
    }


def test_render_execution_and_qc_fail_closed() -> None:
    with pytest.raises(ValidationError, match="output and checksum"):
        RenderExecutionReport(
            render_plan_ref=ref("RenderPlan"),
            attempt=1,
            duration_ms=10,
            peak_memory_bytes=1,
            ffmpeg_version="8.1.2",
            succeeded=True,
        )
    failed = TechnicalCheck(
        check_id="duration",
        status="failed",
        measured={},
        profile_ref=ref("ConfigArtifact"),
        blocker=True,
        detail="duration mismatch",
    )
    with pytest.raises(ValidationError, match="inverse of blockers"):
        TechnicalQCReport(
            candidate_ref=ref("FinalCandidate"),
            checks=(failed,),
            passed=True,
        )


def test_rights_blockers_propagate_and_release_is_human_only() -> None:
    entry = RightsManifestEntry(
        asset_ref=ref("AudioAssetSelection"),
        role="bgm",
        rights=cleared_rights(),
        release_blockers=("territory",),
    )
    with pytest.raises(ValidationError, match="propagate"):
        ReleaseRightsManifest(
            candidate_ref=ref("FinalCandidate"),
            platform="douyin",
            territory="CN",
            evaluated_at=datetime.now(UTC),
            entries=(entry,),
        )
    with pytest.raises(ValidationError, match="human approver"):
        ReleaseRecord(
            final_candidate_ref=ref("FinalCandidate"),
            candidate_checksum="sha256:abc",
            release_decision_ref=ref("QualityReview"),
            approved_by={"kind": "system", "id": "router"},
            approved_at=datetime.now(UTC),
            platform_profile_ref=ref("ConfigArtifact"),
            rights_manifest_ref=ref("RightsManifest"),
        )


def test_offline_quality_blocker_forces_reject() -> None:
    with pytest.raises(ValidationError, match="require reject"):
        OfflineQualityReview(
            candidate_ref=ref("FinalCandidate"),
            rubric_profile_ref=ref("ConfigArtifact"),
            dimension_scores=(),
            weighted_score=90,
            blocker_codes=("story-error",),
            verdict="pass",
        )
