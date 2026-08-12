"""E11 deterministic render/release preflight; blockers are never score-compensated."""

from __future__ import annotations

from packages.contracts.foundation import ArtifactRef
from packages.contracts.render_release import (
    OfflineQualityReview,
    ReleaseReviewPackage,
    ReleaseRightsManifest,
    TechnicalQCReport,
)


class ReleasePreflightBlocked(RuntimeError):
    pass


def build_release_review_package(
    *,
    final_candidate_ref: ArtifactRef,
    candidate_checksum: str,
    technical_qc_ref: ArtifactRef,
    technical_qc: TechnicalQCReport,
    rights_manifest_ref: ArtifactRef,
    rights_manifest: ReleaseRightsManifest,
    quality_review_ref: ArtifactRef,
    quality_review: OfflineQualityReview,
) -> ReleaseReviewPackage:
    blockers = tuple(
        dict.fromkeys(
            (
                *technical_qc.blocker_codes,
                *rights_manifest.blocker_codes,
                *quality_review.blocker_codes,
            )
        )
    )
    incomplete = (
        not technical_qc.checks
        or not rights_manifest.entries
        or not quality_review.dimension_scores
    )
    return ReleaseReviewPackage(
        final_candidate_ref=final_candidate_ref,
        candidate_checksum=candidate_checksum,
        technical_qc_ref=technical_qc_ref,
        rights_manifest_ref=rights_manifest_ref,
        quality_review_ref=quality_review_ref,
        blocker_codes=blockers,
        incomplete=incomplete,
    )


def assert_release_eligible(package: ReleaseReviewPackage) -> None:
    if package.incomplete or package.blocker_codes:
        raise ReleasePreflightBlocked(
            "incomplete or blocked candidate cannot enter Release approval"
        )
