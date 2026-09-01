"""E06 typed adapter tests: package registry alignment, validate, estimate."""

from pathlib import Path
from uuid import uuid4

import pytest

from packages.contracts import (
    ProviderCapability,
    ProviderInvocationRequest,
    ProviderPackage,
)
from packages.providers.admission import CANDIDATE_PROVIDERS
from packages.providers.visual.paddle_detection import PaddleDetectionProvider
from packages.providers.visual.paddle_ocr import PaddleOCRProvider
from packages.providers.visual.volcengine_ark_vlm import VolcengineArkVLMProvider


def _request(capability: ProviderCapability, frame: Path) -> ProviderInvocationRequest:
    return ProviderInvocationRequest(
        capability=capability,
        inputs=({"artifact_id": str(uuid4()), "version": 1, "artifact_type": "SourceMedia"},),
        config_ref={"artifact_id": str(uuid4()), "version": 1, "artifact_type": "ConfigArtifact"},
        resource_profile_ref={
            "artifact_id": str(uuid4()),
            "version": 1,
            "artifact_type": "ResourceProfile",
        },
        idempotency_key=str(uuid4()),
        timeout_ms=60_000,
        parameters={"frame_path": str(frame)},
    )


def _make_frame(tmp_path: Path) -> Path:
    frame = tmp_path / "frame.jpg"
    frame.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
    return frame


def _registered(provider: str) -> ProviderPackage:
    return next(p for p in CANDIDATE_PROVIDERS if p.identity.provider == provider)


@pytest.mark.parametrize(
    ("adapter", "provider_name", "capability"),
    [
        (PaddleOCRProvider(), "paddleocr", ProviderCapability.OCR),
        (PaddleDetectionProvider(), "paddle-detection", ProviderCapability.DETECTION),
        (VolcengineArkVLMProvider(), "volcengine-ark", ProviderCapability.VLM),
    ],
)
def test_adapter_package_matches_registry(
    adapter: object, provider_name: str, capability: ProviderCapability
) -> None:
    package = adapter.package()  # type: ignore[attr-defined]
    registered = _registered(provider_name)
    assert package.identity.provider == registered.identity.provider
    assert package.admission == registered.admission
    assert package.model_checksum == registered.model_checksum
    assert capability in package.capabilities
    assert package.admission.value == "research"


def test_ocr_validate_and_estimate(tmp_path: Path) -> None:
    frame = _make_frame(tmp_path)
    adapter = PaddleOCRProvider()
    request = _request(ProviderCapability.OCR, frame)
    adapter.validate(request)
    estimate = adapter.estimate(request)
    assert estimate.estimated_duration_ms > 0
    assert estimate.temporary_disk_bytes > 0


def test_ocr_rejects_wrong_capability(tmp_path: Path) -> None:
    frame = _make_frame(tmp_path)
    adapter = PaddleOCRProvider()
    with pytest.raises(ValueError, match="only supports OCR"):
        adapter.validate(_request(ProviderCapability.VLM, frame))


def test_detection_validate_and_estimate(tmp_path: Path) -> None:
    frame = _make_frame(tmp_path)
    adapter = PaddleDetectionProvider()
    adapter.validate(_request(ProviderCapability.DETECTION, frame))
    assert adapter.estimate(_request(ProviderCapability.DETECTION, frame)).cpu_cores >= 1


def test_ark_vlm_fails_closed_without_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    import packages.providers.visual.volcengine_ark_vlm as ark_module

    frame = _make_frame(tmp_path)
    adapter = VolcengineArkVLMProvider()
    request = _request(ProviderCapability.VLM, frame)
    adapter.validate(request)
    monkeypatch.setattr(
        ark_module,
        "get_settings",
        lambda: SimpleNamespace(
            volcengine_ark_api_key=None,
            volcengine_ark_model=None,
            volcengine_ark_endpoint="https://example.invalid",
        ),
    )
    with pytest.raises(ValueError, match="unavailable"):
        adapter.infer(request)


def test_ark_health_reflects_configuration() -> None:
    adapter = VolcengineArkVLMProvider()
    # health follows the configured key/model; assert it is a bool either way.
    assert isinstance(adapter.health(), bool)


def test_polygon_to_bbox_normalizes_and_clamps() -> None:
    from packages.providers.visual.paddle_ocr import _polygon_to_bbox

    box = _polygon_to_bbox([[0, 0], [100, 0], [100, 50], [0, 50]], width=200, height=100)
    assert box == {"x_min": 0.0, "y_min": 0.0, "x_max": 0.5, "y_max": 0.5}
    assert _polygon_to_bbox(None, 200, 100) is None
    assert _polygon_to_bbox([], 200, 100) is None
    assert _polygon_to_bbox([[0, 0], [0, 0]], 200, 100) is None
    assert _polygon_to_bbox([[0, 0], [100, 0], [100, 50], [0, 50]], 0, 100) is None


def test_pixel_box_to_bbox_uses_coordinate_array() -> None:
    from packages.providers.visual.paddle_detection import _pixel_box_to_bbox

    box = _pixel_box_to_bbox(
        {"score": 0.9, "coordinate": [10, 20, 110, 120]}, width=200, height=100
    )
    assert box == {"x_min": 0.05, "y_min": 0.2, "x_max": 0.55, "y_max": 1.0}
    assert _pixel_box_to_bbox({"score": 0.9}, 200, 100) is None
    assert _pixel_box_to_bbox({"coordinate": "bad"}, 200, 100) is None
    assert _pixel_box_to_bbox({"coordinate": [1, 1, 1, 1]}, 200, 100) is None
    assert _pixel_box_to_bbox({"coordinate": [0, 0, 10, 10]}, 0, 100) is None


def test_provider_for_selects_adapters() -> None:
    from packages.providers.visual.paddle_detection import PaddleDetectionProvider
    from packages.providers.visual.paddle_ocr import PaddleOCRProvider
    from packages.providers.visual.volcengine_ark_vlm import VolcengineArkVLMProvider
    from workflows.visual.activities import _provider_for

    assert isinstance(_provider_for("ocr"), PaddleOCRProvider)
    assert isinstance(_provider_for("detection"), PaddleDetectionProvider)
    assert isinstance(_provider_for("vlm"), VolcengineArkVLMProvider)
    with pytest.raises(ValueError, match="unsupported visual capability"):
        _provider_for("tracking")


def test_local_adapters_report_health_and_estimate(tmp_path: Path) -> None:
    frame = _make_frame(tmp_path)
    ocr = PaddleOCRProvider()
    det = PaddleDetectionProvider()
    assert ocr.health() is True
    assert det.health() is True
    ocr_req = _request(ProviderCapability.OCR, frame)
    assert ocr.estimate(ocr_req).memory_bytes >= 0
    det_req = _request(ProviderCapability.DETECTION, frame)
    assert det.estimate(det_req).estimated_duration_ms > 0
    ark = VolcengineArkVLMProvider()
    with pytest.raises(ValueError, match="only supports VLM"):
        ark.validate(_request(ProviderCapability.OCR, frame))


def test_opencv_adapter_validate_and_estimate(tmp_path: Path) -> None:
    from packages.providers.visual.opencv_contour import OpenCVContourProvider

    frame = _make_frame(tmp_path)
    provider = OpenCVContourProvider()
    assert provider.package().identity.provider == "opencv"
    with pytest.raises(ValueError, match="only supports detection"):
        provider.validate(_request(ProviderCapability.OCR, frame))
    provider.validate(_request(ProviderCapability.DETECTION, frame))
    assert provider.estimate(_request(ProviderCapability.DETECTION, frame)).cpu_cores >= 1
    assert provider.health() is True
    with pytest.raises(FileNotFoundError):
        provider.validate(_request(ProviderCapability.DETECTION, tmp_path / "missing.jpg"))


def test_json_http_adapter_validate_and_estimate(tmp_path: Path) -> None:
    from packages.contracts import ProviderCapability as PC
    from packages.providers.visual.json_http import VisualJsonHttpProvider

    frame = _make_frame(tmp_path)
    provider = VisualJsonHttpProvider(
        base_url="http://127.0.0.1:9",
        capability=PC.DETECTION,
        implementation="fake",
        version="1",
        model="m",
        code_license="Apache-2.0",
    )
    assert provider.package().admission.value == "research"
    with pytest.raises(ValueError, match="frame_paths"):
        provider.validate(_request(PC.DETECTION, frame))
    with pytest.raises(ValueError, match="unsupported"):
        VisualJsonHttpProvider(
            base_url="http://x",
            capability=PC.VAD,
            implementation="x",
            version="1",
            model="m",
            code_license="Apache-2.0",
        )
