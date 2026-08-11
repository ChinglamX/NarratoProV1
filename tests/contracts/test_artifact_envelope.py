from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import ArtifactEnvelope, ArtifactRef, Checksum, ProducerRecord


def ref(kind: str = "SourceMedia", version: int = 1) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": uuid4(), "version": version, "artifact_type": kind}
    )


def producer() -> ProducerRecord:
    return ProducerRecord.model_validate(
        {
            "module": "ingest",
            "module_version": "1.0.0",
            "resource_profile_ref": ref("ResourceProfile"),
        }
    )


def envelope(**overrides: object) -> ArtifactEnvelope:
    values: dict[str, object] = {
        "artifact_id": uuid4(),
        "artifact_type": "MediaProbe",
        "schema_version": "1.0.0",
        "version": 1,
        "project_id": uuid4(),
        "run_id": uuid4(),
        "state": "committed",
        "created_at": datetime(2026, 8, 12, tzinfo=UTC),
        "created_by": {"kind": "system", "id": "ingest-worker"},
        "producer": producer(),
        "checksum": "sha256:" + "a" * 64,
        "rights_class": "source-restricted",
        "trace_id": "1" * 32,
        "payload": {"duration": 100},
    }
    values.update(overrides)
    return ArtifactEnvelope.model_validate(values)


def test_artifact_envelope_round_trip_and_exact_ref() -> None:
    value = envelope()
    restored = ArtifactEnvelope.model_validate_json(value.canonical_json())
    assert restored == value
    assert restored.as_ref().checksum == Checksum("sha256:" + "a" * 64)


def test_artifact_envelope_requires_payload_and_utc() -> None:
    with pytest.raises(ValidationError, match="payload or payload_uri"):
        envelope(payload=None)
    with pytest.raises(ValidationError, match="UTC"):
        envelope(created_at=datetime(2026, 8, 12))


def test_artifact_envelope_rejects_duplicate_and_future_self_input() -> None:
    upstream = ref()
    with pytest.raises(ValidationError, match="unique"):
        envelope(inputs=(upstream, upstream))
    artifact_id = uuid4()
    with pytest.raises(ValidationError, match="current or future"):
        envelope(
            artifact_id=artifact_id,
            inputs=(
                ArtifactRef.model_validate(
                    {"artifact_id": artifact_id, "version": 1, "artifact_type": "MediaProbe"}
                ),
            ),
        )


def test_artifact_dependency_rejects_self_reference() -> None:
    from packages.contracts import ArtifactDependency

    target = ref()
    dependency = ArtifactDependency.model_validate(
        {
            "upstream": target,
            "downstream": ref("MediaProbe"),
            "dependency_type": "media",
            "invalidation_rule": "source-change",
        }
    )
    assert ArtifactDependency.model_validate_json(dependency.canonical_json()) == dependency
    with pytest.raises(ValidationError, match="itself"):
        ArtifactDependency.model_validate(
            {
                "upstream": target,
                "downstream": target,
                "dependency_type": "semantic",
                "invalidation_rule": "source-change",
            }
        )
