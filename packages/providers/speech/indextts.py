"""IndexTTS-2 provider adapter (E10 research; local voice cloning).

Talks to the locally hosted IndexTTS-2 service (http://127.0.0.1:8081/tts,
multipart: text + reference audio -> WAV bytes) using the reference voice
``ref_7_clean.wav`` (project-owner approved 2026-08-16). Follows the same
ProviderPort shape as the visual adapters; the service itself lives outside
this repo (NarratoPro toolchain), so this module is a thin typed client.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from pathlib import Path

from packages.contracts import (
    ProviderCapability,
    ProviderInvocationRequest,
    ProviderPackage,
    ProviderResourceEstimate,
)
from packages.foundation.settings import get_settings
from packages.providers import ProviderRawOutput
from packages.providers.admission import CANDIDATE_PROVIDERS

_PROVIDER = "indextts"


def _registered_package() -> ProviderPackage:
    return next(p for p in CANDIDATE_PROVIDERS if p.identity.provider == _PROVIDER).model_copy(
        deep=True
    )


def _reference_audio() -> Path:
    value = get_settings().indextts_ref_audio
    path = Path(value).resolve(strict=True)
    if not path.is_file() or path.is_symlink():
        raise ValueError("IndexTTS reference audio must be a regular file")
    return path


def _api_url() -> str:
    return get_settings().indextts_api_url


class IndexTTSProvider:
    """Local IndexTTS-2 voice-clone adapter; research admission only.

    The synthesis request carries the reference voice (``ref_7_clean.wav``) and
    returns WAV bytes; the raw output payload is the WAV file content so the
    caller can persist it as a VoiceTake audio blob.
    """

    def package(self) -> ProviderPackage:
        return _registered_package()

    def validate(self, request: ProviderInvocationRequest) -> None:
        if request.capability is not ProviderCapability.TTS:
            raise ValueError("IndexTTS provider only supports TTS")
        text = request.parameters.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("IndexTTS request requires parameters.text")

    def estimate(self, request: ProviderInvocationRequest) -> ProviderResourceEstimate:
        return ProviderResourceEstimate(
            cpu_cores=1,
            memory_bytes=4 * 1024**3,  # IndexTTS-2 service footprint
            accelerator=None,
            accelerator_memory_bytes=0,
            temporary_disk_bytes=64 * 1024**2,
            estimated_duration_ms=30_000,
            estimated_cost_micros=0,  # local service
        )

    def health(self) -> bool:
        # Derive the health endpoint from the API base host (never string-
        # replace the path: a hostname containing "tts" would corrupt the URL).
        from urllib.parse import urlparse, urlunparse

        api = urlparse(_api_url())
        health_url = urlunparse(api._replace(path="/health"))
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(health_url, timeout=5) as response:
                status = int(response.status)
                return status == 200
        except Exception:
            return False

    def infer(self, request: ProviderInvocationRequest) -> ProviderRawOutput:
        text = str(request.parameters.get("text") or "").strip()
        if not text:
            raise ValueError("IndexTTS request requires parameters.text")
        ref_audio = _reference_audio()
        started = time.monotonic()
        body, content_type = _encode_multipart(text=text, ref_audio=ref_audio)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        req = urllib.request.Request(
            _api_url(),
            data=body,
            method="POST",
            headers={"Content-Type": content_type, "Content-Length": str(len(body))},
        )
        try:
            with opener.open(req, timeout=600) as response:
                content = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"IndexTTS HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot connect to IndexTTS at {_api_url()}: {exc.reason}") from exc
        if not content:
            raise RuntimeError("IndexTTS returned empty synthesis")
        return ProviderRawOutput(
            payload=content,  # WAV bytes
            media_type="audio/wav",
            schema_version="1.0.0",
            duration_ms=int((time.monotonic() - started) * 1000),
            cost_micros=0,
        )


def _encode_multipart(*, text: str, ref_audio: Path) -> tuple[bytes, str]:
    """Build a multipart/form-data body: text fields + reference audio file."""
    import uuid

    boundary = f"----indextts-{uuid.uuid4().hex}"
    lines: list[bytes] = []
    fields: dict[str, str] = {
        "text": text,
        "infer_mode": "普通推理",
        "temperature": "1.0",
        "top_p": "0.8",
        "top_k": "30",
        "do_sample": "true",
        "num_beams": "1",
        "repetition_penalty": "10.0",
    }
    for key, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(
        (
            f'Content-Disposition: form-data; name="prompt_audio"; '
            f'filename="{ref_audio.name}"\r\nContent-Type: audio/wav\r\n\r\n'
        ).encode()
    )
    lines.append(ref_audio.read_bytes())
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    return b"".join(lines), f"multipart/form-data; boundary={boundary}"
