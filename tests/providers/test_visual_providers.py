import json
from pathlib import Path
from urllib.request import Request
from uuid import uuid4

import cv2
import numpy as np

from packages.contracts import ArtifactRef, ProviderCapability, ProviderInvocationRequest
from packages.providers.visual import OpenCVContourProvider, VisualJsonHttpProvider


def ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def request(path: Path, capability: str = "detection") -> ProviderInvocationRequest:
    return ProviderInvocationRequest.model_validate(
        {
            "capability": capability,
            "inputs": [ref("ProxyMedia")],
            "config_ref": ref("EffectiveConfigSnapshot"),
            "resource_profile_ref": ref("ResourceProfile"),
            "idempotency_key": f"visual-{capability}-test",
            "timeout_ms": 10_000,
            "parameters": {"frame_path": str(path), "frame_paths": [str(path)]},
        }
    )


def test_opencv_contour_runs_real_decode_and_remains_research(tmp_path: Path) -> None:
    path = tmp_path / "frame.png"
    image = np.full((256, 128, 3), 127, dtype=np.uint8)
    assert cv2.imwrite(str(path), image)
    provider = OpenCVContourProvider()
    invocation = request(path)
    provider.validate(invocation)
    output = provider.infer(invocation)
    payload = json.loads(output.payload)
    assert provider.package().admission == "research"
    assert payload["detections"] == []
    assert 0.49 < payload["quality"]["mean_luminance"] < 0.51
    assert output.duration_ms > 0


def test_visual_http_provider_is_capability_scoped_and_research(tmp_path: Path) -> None:
    path = tmp_path / "frame.png"
    path.write_bytes(b"fixture")
    provider = VisualJsonHttpProvider(
        base_url="http://127.0.0.1:9999",
        capability=ProviderCapability.OCR,
        implementation="paddleocr",
        version="3.x-unpinned",
        model="PP-OCRv5",
        code_license="Apache-2.0",
    )
    invocation = request(path, "ocr")
    provider.validate(invocation)
    assert provider.package().admission == "research"
    assert provider.estimate(invocation).accelerator == "metal"
    assert provider.health() is False
    assert isinstance(Request("http://example.invalid"), Request)
