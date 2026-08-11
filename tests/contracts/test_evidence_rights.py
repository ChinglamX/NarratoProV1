from datetime import UTC, datetime
from math import inf, nan
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    ArtifactRef,
    ConfidenceRecord,
    EvidenceLink,
    EvidenceType,
    FrameRange,
    RightsGrantRef,
    RightsManifestRef,
    RightsMetadata,
)


def artifact_ref(artifact_type: str = "SourceMedia") -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=artifact_type)


def evidence() -> EvidenceLink:
    return EvidenceLink(
        evidence_id=uuid4(),
        source=artifact_ref(),
        evidence_type=EvidenceType.DIALOGUE,
        excerpt="你终于回来了",
    )


def confidence(**overrides: object) -> ConfidenceRecord:
    values: dict[str, object] = {
        "score": 0.72,
        "status": "shadow",
        "method": "cross-modal-consistency-v1",
        "calibration_version": None,
        "applicable_scope": "task=dialogue;genre=period;provider=funasr-v1",
        "risk_class": "medium",
        "evidence": (evidence(),),
    }
    values.update(overrides)
    return ConfidenceRecord.model_validate(values)


def test_artifact_level_evidence_is_valid_but_frame_ranges_are_strict() -> None:
    artifact_evidence = EvidenceLink(
        evidence_id=uuid4(),
        source=artifact_ref("MediaProbe"),
        evidence_type="metadata",
    )
    assert artifact_evidence.source_range is None
    with pytest.raises(ValidationError, match="end_frame"):
        FrameRange(start_frame=10, end_frame=10)


@pytest.mark.parametrize("score", [-0.01, 1.01, nan, inf, -inf])
def test_confidence_rejects_invalid_scores(score: float) -> None:
    with pytest.raises(ValidationError):
        confidence(score=score)


def test_unavailable_confidence_has_no_score_or_calibration_claim() -> None:
    unavailable = confidence(
        score=None,
        status="unavailable",
        method="required-detector-unavailable",
    )
    assert unavailable.score is None

    with pytest.raises(ValidationError, match="must not include a score"):
        confidence(status="unavailable")
    with pytest.raises(ValidationError, match="must not claim calibration"):
        confidence(
            score=None,
            status="unavailable",
            calibration_version="cal-v1",
        )


def test_shadow_cannot_claim_production_calibration() -> None:
    with pytest.raises(ValidationError, match="shadow confidence"):
        confidence(calibration_version="cal-v1")


def test_calibrated_confidence_requires_version_and_scope() -> None:
    with pytest.raises(ValidationError, match="calibration_version"):
        confidence(status="calibrated")
    with pytest.raises(ValidationError):
        confidence(applicable_scope="")
    calibrated = confidence(status="calibrated", calibration_version="cal-v1")
    assert calibrated.calibration_version == "cal-v1"
    assert ConfidenceRecord.model_validate_json(calibrated.canonical_json()) == calibrated


def test_drifted_confidence_references_the_invalidated_calibration() -> None:
    with pytest.raises(ValidationError, match="drifted confidence"):
        confidence(status="drifted")
    drifted = confidence(status="drifted", calibration_version="cal-v1")
    assert drifted.calibration_version == "cal-v1"


def test_unknown_rights_fail_closed_for_release() -> None:
    unknown = RightsMetadata(status="unknown", checked_at=datetime(2026, 8, 11, tzinfo=UTC))
    blockers = unknown.release_blockers(
        at=datetime(2026, 8, 12, tzinfo=UTC),
        platform="douyin",
        territory="CN",
    )
    assert "rights_status:unknown" in blockers
    assert blockers


@pytest.mark.parametrize("status", ["restricted", "expired", "revoked"])
def test_non_cleared_rights_statuses_block_release(status: str) -> None:
    metadata = RightsMetadata(status=status, checked_at=datetime(2026, 8, 11, tzinfo=UTC))
    assert f"rights_status:{status}" in metadata.release_blockers(
        at=datetime(2026, 8, 12, tzinfo=UTC),
        platform="douyin",
        territory="CN",
    )


def test_cleared_rights_require_auditable_scope_and_grant() -> None:
    with pytest.raises(ValidationError, match="grant_ref"):
        RightsMetadata(
            status="cleared",
            source="licensed-library",
            license="commercial-v1",
            territories=frozenset({"CN"}),
            platforms=frozenset({"douyin"}),
            commercial_use=True,
            modification=True,
            synchronization=True,
            checked_at=datetime(2026, 8, 11, tzinfo=UTC),
        )


def test_cleared_rights_are_evaluated_at_explicit_time_and_scope() -> None:
    metadata = RightsMetadata(
        status="cleared",
        source="licensed-library",
        license="commercial-v1",
        grant_ref=RightsGrantRef(artifact_id=uuid4(), version=2),
        territories=frozenset({"CN"}),
        platforms=frozenset({"douyin"}),
        commercial_use=True,
        modification=True,
        synchronization=True,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=datetime(2027, 1, 1, tzinfo=UTC),
        checked_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    assert not metadata.release_blockers(
        at=datetime(2026, 8, 12, tzinfo=UTC), platform="douyin", territory="CN"
    )
    assert "rights_expired" in metadata.release_blockers(
        at=datetime(2027, 1, 1, tzinfo=UTC), platform="douyin", territory="CN"
    )
    assert "platform_out_of_scope" in metadata.release_blockers(
        at=datetime(2026, 8, 12, tzinfo=UTC), platform="youtube", territory="CN"
    )


def test_rights_restrictions_require_release_review() -> None:
    metadata = RightsMetadata(
        status="cleared",
        source="licensed-library",
        license="commercial-v1",
        grant_ref=RightsGrantRef(artifact_id=uuid4(), version=2),
        territories=frozenset({"CN"}),
        platforms=frozenset({"douyin"}),
        commercial_use=True,
        modification=True,
        synchronization=True,
        restrictions=("no-paid-boosting",),
        checked_at=datetime(2026, 8, 11, tzinfo=UTC),
    )
    assert "rights_restrictions_require_review" in metadata.release_blockers(
        at=datetime(2026, 8, 12, tzinfo=UTC), platform="douyin", territory="CN"
    )


def test_rights_timestamps_must_be_utc() -> None:
    with pytest.raises(ValidationError, match="must use UTC"):
        RightsMetadata(status="unknown", checked_at=datetime(2026, 8, 11))


def test_rights_manifest_ref_is_type_safe_and_canonical() -> None:
    ref = RightsManifestRef(artifact_id=uuid4(), version=3)
    assert ref.artifact_type == "RightsManifest"
    assert RightsManifestRef.model_validate_json(ref.canonical_json()) == ref
    with pytest.raises(ValidationError):
        RightsManifestRef(
            artifact_id=uuid4(),
            version=1,
            artifact_type="RightsGrant",  # type: ignore[arg-type]
        )
