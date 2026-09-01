"""E11 render activity helper tests (pure functions, Temporal bodies pragma'd).

The activity bodies (execute_render_activity / technical_qc_activity) are
verified by real Temporal runs; this module covers the pure helpers only.
"""

from uuid import uuid4

from packages.contracts.foundation import ArtifactRef
from workflows.production.render_activities import (
    _int_measure,
    _pointer,
    _ref,
)
from workflows.project.models import ArtifactPointer


def _ref_value() -> ArtifactRef:
    return ArtifactRef.model_validate(
        {
            "artifact_id": str(uuid4()),
            "version": 3,
            "artifact_type": "RenderPlan",
            "checksum": "sha256:" + "a" * 64,
        }
    )


def test_ref_pointer_roundtrip() -> None:
    reference = _ref_value()
    pointer = _pointer(reference)
    assert isinstance(pointer, ArtifactPointer)
    assert pointer.version == 3
    assert pointer.artifact_type == "RenderPlan"
    assert pointer.checksum == str(reference.checksum)
    assert _ref(pointer) == reference


def test_pointer_without_checksum() -> None:
    reference = ArtifactRef.model_validate(
        {
            "artifact_id": str(uuid4()),
            "version": 3,
            "artifact_type": "RenderPlan",
        }
    )
    pointer = _pointer(reference)
    assert pointer.checksum is None


def test_int_measure() -> None:
    assert _int_measure(1920) == 1920
    assert _int_measure("1080") == 1080
    assert _int_measure(None) == 0
    assert _int_measure(0) == 0
