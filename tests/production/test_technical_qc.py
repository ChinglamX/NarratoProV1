from datetime import UTC, datetime
from uuid import uuid4

from packages.contracts import ArtifactRef, RightsMetadata
from packages.production.technical_qc import rights_manifest, technical_qc


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def test_technical_qc_and_unknown_rights_fail_closed() -> None:
    report = technical_qc(
        candidate_ref=ref("FinalCandidate"),
        profile_ref=ref("ConfigArtifact"),
        measured={"width": 720, "codec": "h264"},
        required={"width": 720, "codec": "h265"},
    )
    assert not report.passed and report.blocker_codes == ("technical:codec",)
    manifest = rights_manifest(
        candidate_ref=ref("FinalCandidate"),
        platform="douyin",
        territory="CN",
        evaluated_at=datetime.now(UTC),
        assets=(
            (
                ref("SourceMedia"),
                "video",
                RightsMetadata(status="unknown", checked_at=datetime.now(UTC)),
            ),
        ),
    )
    assert manifest.blocker_codes and manifest.entries[0].release_blockers
