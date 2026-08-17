"""IndexTTS adapter unit tests (mock HTTP; no live service needed)."""

from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from packages.contracts import ArtifactRef, ProviderCapability, ProviderInvocationRequest
from packages.providers.speech.indextts import IndexTTSProvider, _encode_multipart


def _ref(kind: str = "NarrationLineSet") -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": str(uuid4()), "version": 1, "artifact_type": kind}
    )


def _request(text: str = "你好") -> ProviderInvocationRequest:
    return ProviderInvocationRequest(
        capability=ProviderCapability.TTS,
        inputs=(_ref(),),
        config_ref=_ref("ConfigArtifact"),
        resource_profile_ref=_ref("ResourceProfile"),
        idempotency_key=f"test-tts-{uuid4()}",
        timeout_ms=600_000,
        parameters={"text": text},
    )


def test_registered_package_matches_registry() -> None:
    provider = IndexTTSProvider()
    package = provider.package()
    assert package.identity.provider == "indextts"
    assert "tts" in package.capabilities
    assert package.commercial_use_allowed is True  # owner-approved 2026-08-16


def test_validate_requires_tts_capability_and_text() -> None:
    provider = IndexTTSProvider()
    with pytest.raises(ValueError, match="only supports TTS"):
        provider.validate(_request().model_copy(update={"capability": ProviderCapability.OCR}))
    with pytest.raises(ValueError, match=r"requires parameters.text"):
        provider.validate(_request().model_copy(update={"parameters": {}}))


def test_estimate_is_local_and_zero_cost() -> None:
    estimate = IndexTTSProvider().estimate(_request())
    assert estimate.estimated_cost_micros == 0
    assert estimate.estimated_duration_ms > 0


def test_health_false_when_service_down() -> None:
    with patch(
        "packages.providers.speech.indextts._api_url", return_value="http://127.0.0.1:1/tts"
    ):
        assert IndexTTSProvider().health() is False


def test_infer_parses_wav_bytes_from_response(tmp_path: Path) -> None:
    wav = b"RIFF\x00\x00\x00\x00WAVEfmt"  # stand-in WAV bytes

    class _Response:
        status = 200

        def read(self) -> bytes:
            return wav

        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class _Opener:
        def open(self, request: object, timeout: int = 0) -> _Response:
            return _Response()

    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFF")
    provider = IndexTTSProvider()
    with (
        patch(
            "packages.providers.speech.indextts._api_url",
            return_value="http://127.0.0.1:8081/tts",
        ),
        patch(
            "packages.providers.speech.indextts._reference_audio",
            return_value=ref,
        ),
        patch(
            "packages.providers.speech.indextts.urllib.request.build_opener",
            return_value=_Opener(),
        ),
    ):
        raw = provider.infer(_request(text="你好世界"))
    assert raw.payload == wav
    assert raw.media_type == "audio/wav"
    assert raw.cost_micros == 0


def test_multipart_contains_prompt_audio_field(tmp_path: Path) -> None:
    ref = tmp_path / "ref.wav"
    ref.write_bytes(b"RIFF")
    body, content_type = _encode_multipart(text="你好", ref_audio=ref)
    assert 'name="prompt_audio"' in body.decode("utf-8", errors="replace")
    assert "multipart/form-data" in content_type
    assert ref.read_bytes() in body
