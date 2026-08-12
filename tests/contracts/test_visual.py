from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    ArtifactRef,
    BoundingBox,
    SupplementarySampleRequest,
    VisualEmbedding,
    VisualObservation,
    VLMClaim,
)


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def frame() -> dict[str, object]:
    return {
        "frame_ref": ref("ProxyMedia"),
        "sample_id": uuid4(),
        "source_time": {"value": 25, "rate_num": 25},
    }


def confidence() -> dict[str, object]:
    return {
        "score": 0.8,
        "status": "shadow",
        "method": "uncalibrated",
        "applicable_scope": "visual-test",
        "risk_class": "high",
    }


def test_visual_contracts_enforce_geometry_embedding_and_evidence() -> None:
    with pytest.raises(ValidationError, match="positive normalized area"):
        BoundingBox(x_min=0.5, y_min=0.1, x_max=0.5, y_max=0.9)
    embedding = VisualEmbedding.model_validate(
        {
            "embedding_id": uuid4(),
            "frame": frame(),
            "vector": [0.0, 1.0],
            "dimensions": 2,
            "normalized": True,
            "provider": {
                "provider": "clip",
                "implementation": "test",
                "version": "1",
                "license": "test-only",
            },
        }
    )
    assert embedding.dimensions == 2
    with pytest.raises(ValidationError, match="visible VLM claims require frame evidence"):
        VLMClaim.model_validate(
            {
                "claim_id": uuid4(),
                "kind": "visible",
                "statement": "a person is visible",
                "frame_evidence": [],
                "confidence": confidence(),
            }
        )


def test_unavailable_and_supplementary_budget_fail_closed() -> None:
    observation = VisualObservation.model_validate(
        {
            "source_ref": ref("SourceMedia"),
            "frame_plan_ref": ref("FrameSamplePlan"),
            "raw_response_refs": [],
            "status": "unavailable",
            "unavailable_capabilities": ["ocr", "vlm"],
        }
    )
    assert observation.status == "unavailable"
    with pytest.raises(ValidationError, match="exceeds remaining budget"):
        SupplementarySampleRequest.model_validate(
            {
                "request_id": uuid4(),
                "source_ref": ref("SourceMedia"),
                "shot_ref": ref("SceneShotCatalog"),
                "reason": "low-face-quality",
                "expected_uncertainty_reduction": "find a frontal face",
                "requested_times": [
                    {"value": 1, "rate_num": 1},
                    {"value": 2, "rate_num": 1},
                ],
                "remaining_shot_budget": 1,
            }
        )
