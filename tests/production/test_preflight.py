import pytest

from packages.contracts import ArtifactRef
from packages.contracts.render_release import (
    OfflineQualityReview,
    ReleaseRightsManifest,
    TechnicalQCReport,
)
from packages.production.preflight import (
    ReleasePreflightBlocked,
    assert_release_eligible,
    build_release_review_package,
)


def ref(kind: str) -> ArtifactRef:
    from uuid import uuid4

    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def test_preflight_aggregates_blockers_without_score_compensation() -> None:
    technical = TechnicalQCReport(
        candidate_ref=ref("FinalCandidate"), checks=(), blocker_codes=("sync",), passed=False
    )
    rights = ReleaseRightsManifest.model_construct(
        candidate_ref=ref("FinalCandidate"),
        platform="douyin",
        territory="CN",
        evaluated_at=None,
        entries=(),
        blocker_codes=("rights",),
    )
    quality = OfflineQualityReview(
        candidate_ref=ref("FinalCandidate"),
        rubric_profile_ref=ref("ConfigArtifact"),
        dimension_scores=(),
        weighted_score=95,
        blocker_codes=("story",),
        verdict="reject",
    )
    package = build_release_review_package(
        final_candidate_ref=ref("FinalCandidate"),
        candidate_checksum="sha256:abc",
        technical_qc_ref=ref("TechnicalQCReport"),
        technical_qc=technical,
        rights_manifest_ref=ref("RightsManifest"),
        rights_manifest=rights,
        quality_review_ref=ref("QualityReview"),
        quality_review=quality,
    )
    assert package.blocker_codes == ("sync", "rights", "story") and package.incomplete
    with pytest.raises(ReleasePreflightBlocked):
        assert_release_eligible(package)
