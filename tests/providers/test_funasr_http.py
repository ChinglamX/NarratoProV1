import json
from pathlib import Path
from uuid import uuid4

import pytest

from packages.contracts import ProviderInvocationRequest
from packages.providers.speech import FunASRHttpProvider


def request(audio: Path) -> ProviderInvocationRequest:
    return ProviderInvocationRequest.model_validate(
        {
            "capability": "asr",
            "inputs": [{"artifact_id": uuid4(), "version": 1, "artifact_type": "AudioStem"}],
            "config_ref": {
                "artifact_id": uuid4(),
                "version": 1,
                "artifact_type": "ConfigArtifact",
            },
            "resource_profile_ref": {
                "artifact_id": uuid4(),
                "version": 1,
                "artifact_type": "ResourceProfile",
            },
            "idempotency_key": "asr:fixture",
            "timeout_ms": 1000,
            "parameters": {"audio_path": str(audio)},
        }
    )


class Response:
    status = 200

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return self.payload


def test_funasr_http_provider_is_research_until_weights_are_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF-fixture")
    provider = FunASRHttpProvider()
    assert provider.package().admission == "research"
    monkeypatch.setattr(
        "packages.providers.speech.funasr_http.urllib.request.urlopen",
        lambda *_a, **_k: Response(json.dumps({"text": "你好", "duration": 1}).encode()),
    )
    provider.validate(request(audio))
    assert provider.health()
    output = provider.infer(request(audio))
    assert json.loads(output.payload)["text"] == "你好"
    assert b"verbose_json" in provider._multipart("boundary", audio)


def test_funasr_provider_rejects_missing_audio_path(tmp_path: Path) -> None:
    provider = FunASRHttpProvider()
    value = request(tmp_path / "will-create.wav")
    with pytest.raises((FileNotFoundError, ValueError)):
        provider.validate(value)


def test_legacy_srt_parser_preserves_timing_and_speaker_cluster() -> None:
    result = FunASRHttpProvider._parse_srt("1\n00:00:01,000 --> 00:00:02,500\n说话人1: 我不答应\n")
    assert result == [{"start": 1.0, "end": 2.5, "text": "我不答应", "speaker": "speaker-1"}]
