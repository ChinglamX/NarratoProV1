"""Volcengine Ark VLM provider adapter (E06 research; hosted Doubao API)."""

from __future__ import annotations

import base64
import json
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

_PROVIDER = "volcengine-ark"


def _registered_package() -> ProviderPackage:
    return next(p for p in CANDIDATE_PROVIDERS if p.identity.provider == _PROVIDER).model_copy(
        deep=True
    )


class VolcengineArkVLMProvider:
    """Hosted VLM (doubao-seed-2-0-mini) via Volcengine Ark chat/completions.

    Requires ``NARRATOPRO_VOLCENGINE_ARK_API_KEY`` and
    ``NARRATOPRO_VOLCENGINE_ARK_MODEL`` in settings (`.env`); without them
    ``infer`` fails closed as unavailable.
    """

    def package(self) -> ProviderPackage:
        return _registered_package()

    @staticmethod
    def _frame_path(request: ProviderInvocationRequest) -> Path:
        value = request.parameters.get("frame_path")
        if not isinstance(value, str):
            raise ValueError("Ark VLM request requires parameters.frame_path")
        path = Path(value).resolve(strict=True)
        if not path.is_file() or path.is_symlink():
            raise ValueError("frame_path must be a regular file")
        return path

    def validate(self, request: ProviderInvocationRequest) -> None:
        if request.capability is not ProviderCapability.VLM:
            raise ValueError("Ark provider only supports VLM")
        self._frame_path(request)

    def estimate(self, request: ProviderInvocationRequest) -> ProviderResourceEstimate:
        size = self._frame_path(request).stat().st_size
        return ProviderResourceEstimate(
            cpu_cores=0,
            memory_bytes=64 * 1024**2,
            temporary_disk_bytes=size,
            estimated_duration_ms=10_000,
        )

    def health(self) -> bool:
        settings = get_settings()
        return settings.volcengine_ark_api_key is not None and bool(settings.volcengine_ark_model)

    def infer(self, request: ProviderInvocationRequest) -> ProviderRawOutput:
        settings = get_settings()
        api_key = settings.volcengine_ark_api_key
        model = settings.volcengine_ark_model
        if api_key is None or not model:
            raise ValueError("Ark VLM is unavailable: API key or model not configured")
        prompt = str(
            request.parameters.get("prompt") or "描述这张画面：人物、场景、文字等主要视觉元素。"  # noqa: RUF001
        )

        started = time.perf_counter()
        with open(self._frame_path(request), "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode()
        body = json.dumps(
            {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            },
            separators=(",", ":"),
        ).encode()
        http_request = urllib.request.Request(  # nosec B310
            settings.volcengine_ark_endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(  # nosec B310
                http_request, timeout=max(10, request.timeout_ms // 1_000)
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raise ValueError(f"Ark VLM request failed ({error.code})") from error
        parsed = json.loads(raw)
        text = parsed["choices"][0]["message"]["content"]
        payload = json.dumps(
            {"vlm_claims": [{"kind": "visible", "statement": text, "score": None}]},
            separators=(",", ":"),
        ).encode()
        elapsed = max(1, round((time.perf_counter() - started) * 1_000))
        return ProviderRawOutput(payload, "application/json", "ark-vlm-v1", elapsed, 0)
