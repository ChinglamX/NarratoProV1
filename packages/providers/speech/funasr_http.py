"""Pinned FunASR 1.3.26 OpenAI-compatible local HTTP adapter."""

from __future__ import annotations

import json
import re
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import cast

from packages.contracts import (
    ProviderInvocationRequest,
    ProviderPackage,
    ProviderResourceEstimate,
)
from packages.providers import ProviderRawOutput


class FunASRHttpProvider:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8000",
        model: str = "sensevoice",
        model_checksum: str | None = None,
        weight_license: str | None = None,
        commercial_use_allowed: bool = False,
        api_mode: str = "openai",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_checksum = model_checksum
        self.weight_license = weight_license
        self.commercial_use_allowed = commercial_use_allowed
        if api_mode not in {"openai", "legacy_narrato"}:
            raise ValueError("unsupported FunASR API mode")
        self.api_mode = api_mode

    def package(self) -> ProviderPackage:
        production = bool(
            self.model_checksum and self.weight_license and self.commercial_use_allowed
        )
        return ProviderPackage.model_validate(
            {
                "identity": {
                    "provider": "funasr",
                    "implementation": "openai-compatible-http",
                    "version": "1.3.26",
                    "model": self.model,
                    "checksum": self.model_checksum,
                    "license": "MIT-code; model-card-governs-weights",
                },
                "capabilities": ["vad", "asr", "alignment"],
                "admission": "production" if production else "research",
                "code_license": "MIT",
                "weight_license": self.weight_license,
                "commercial_use_allowed": self.commercial_use_allowed,
                "model_checksum": self.model_checksum,
                "data_policy": {
                    "execution_location": "local",
                    "allowed_residencies": ["CN", "LOCAL"],
                    "transmits_source_media": False,
                    "retains_input": False,
                },
                "supported_hardware": ["cpu", "cuda"],
                "supported_languages": ["zh-CN", "yue", "en", "ja", "ko"],
                "deterministic": False,
                "retry_safe": True,
                "max_batch_size": 1,
                "known_limitations": [
                    "Model weights require independent model-card license approval",
                    "Provider timestamps remain uncalibrated until G03 benchmark",
                ],
            }
        )

    def _audio_path(self, request: ProviderInvocationRequest) -> Path:
        value = request.parameters.get("audio_path")
        if not isinstance(value, str):
            raise ValueError("FunASR request requires string parameters.audio_path")
        path = Path(value).resolve(strict=True)
        if not path.is_file() or path.is_symlink():
            raise ValueError("FunASR audio_path must be a regular file")
        return path

    def validate(self, request: ProviderInvocationRequest) -> None:
        if request.capability.value not in {"vad", "asr", "alignment"}:
            raise ValueError("FunASR HTTP adapter does not support requested capability")
        self._audio_path(request)

    def estimate(self, request: ProviderInvocationRequest) -> ProviderResourceEstimate:
        size = self._audio_path(request).stat().st_size
        return ProviderResourceEstimate(
            cpu_cores=2,
            memory_bytes=4 * 1024**3,
            temporary_disk_bytes=size,
            estimated_duration_ms=max(1_000, size // 16),
            estimated_cost_micros=0,
        )

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/health", timeout=2) as response:  # nosec B310
                return bool(response.status == 200)
        except (urllib.error.URLError, TimeoutError):
            return False

    def infer(self, request: ProviderInvocationRequest) -> ProviderRawOutput:
        started = time.perf_counter()
        audio = self._audio_path(request)
        boundary = f"----narratopro-{secrets.token_hex(16)}"
        body = self._multipart(boundary, audio)
        endpoint = "/v1/audio/transcriptions" if self.api_mode == "openai" else "/asr"
        http_request = urllib.request.Request(  # nosec B310
            f"{self.base_url}{endpoint}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(  # nosec B310
                http_request, timeout=request.timeout_ms / 1000
            ) as response:
                payload = response.read()
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"FunASR HTTP {error.code}") from error
        parsed = cast(object, json.loads(payload))
        if not isinstance(parsed, dict):
            raise ValueError("FunASR response must be a JSON object")
        if self.api_mode == "legacy_narrato":
            srt_url = parsed.get("srt_url")
            if not isinstance(srt_url, str):
                raise ValueError("legacy FunASR response requires srt_url")
            with urllib.request.urlopen(f"{self.base_url}{srt_url}", timeout=30) as response:  # nosec B310
                srt = response.read().decode("utf-8")
            parsed = {"server_response": parsed, "segments": self._parse_srt(srt)}
            payload = json.dumps(parsed, ensure_ascii=False, separators=(",", ":")).encode()
        schema = "openai-transcription-v1" if self.api_mode == "openai" else "legacy-narrato-srt-v1"
        duration_ms = max(1, round((time.perf_counter() - started) * 1_000))
        return ProviderRawOutput(payload, "application/json", schema, duration_ms, 0)

    def _multipart(self, boundary: str, audio: Path) -> bytes:
        marker = boundary.encode()
        fields = (
            ((b"model", self.model.encode()), (b"response_format", b"verbose_json"))
            if self.api_mode == "openai"
            else ((b"enable_spk", b"true"),)
        )
        chunks: list[bytes] = []
        for name, value in fields:
            chunks.extend(
                [
                    b"--" + marker + b"\r\n",
                    b'Content-Disposition: form-data; name="' + name + b'"\r\n\r\n',
                    value + b"\r\n",
                ]
            )
        chunks.extend(
            [
                b"--" + marker + b"\r\n",
                b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n',
                b"Content-Type: audio/wav\r\n\r\n",
                audio.read_bytes(),
                b"\r\n--" + marker + b"--\r\n",
            ]
        )
        return b"".join(chunks)

    @staticmethod
    def _parse_srt(value: str) -> list[dict[str, object]]:
        pattern = re.compile(
            r"\d+\s*\n(\d{2}:\d{2}:\d{2},\d{3}) --> "
            r"(\d{2}:\d{2}:\d{2},\d{3})\s*\n(.+?)(?=\n\n|\Z)",
            re.DOTALL,
        )

        def seconds(timestamp: str) -> float:
            hours, minutes, tail = timestamp.split(":")
            whole, millis = tail.split(",")
            return int(hours) * 3600 + int(minutes) * 60 + int(whole) + int(millis) / 1000

        result = []
        for start, end, text in pattern.findall(value.strip()):
            speaker = None
            matched = re.match(
                "说话人([^:\N{FULLWIDTH COLON}]+)[:\N{FULLWIDTH COLON}]\\s*(.*)",
                text.strip(),
                re.DOTALL,
            )
            if matched:
                speaker, text = f"speaker-{matched.group(1)}", matched.group(2)
            result.append(
                {
                    "start": seconds(start),
                    "end": seconds(end),
                    "text": text.strip(),
                    "speaker": speaker,
                }
            )
        if not result:
            raise ValueError("legacy FunASR SRT contains no timed segments")
        return result
