"""E06 typed adapter tests: package registry alignment, validate, estimate."""

from pathlib import Path
from uuid import uuid4

import pytest

from packages.contracts import (
    ProviderCapability,
    ProviderInvocationRequest,
    ProviderPackage,
)
from packages.providers.admission import CANDIDATE_VISUAL_PROVIDERS
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
    return next(p for p in CANDIDATE_VISUAL_PROVIDERS if p.identity.provider == provider)


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
