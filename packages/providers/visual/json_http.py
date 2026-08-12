"""Governed JSON HTTP adapter for OCR/detection/tracking/embedding/VLM services."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from packages.contracts import (
    Checksum,
    ProviderCapability,
    ProviderInvocationRequest,
    ProviderPackage,
    ProviderResourceEstimate,
)
from packages.providers import ProviderRawOutput


class VisualJsonHttpProvider:
    def __init__(
        self,
        *,
        base_url: str,
        capability: ProviderCapability,
        implementation: str,
        version: str,
        model: str,
        code_license: str,
        weight_license: str | None = None,
        model_checksum: Checksum | None = None,
        commercial_use_allowed: bool = False,
    ) -> None:
        if capability not in {
            ProviderCapability.OCR,
            ProviderCapability.DETECTION,
            ProviderCapability.TRACKING,
            ProviderCapability.FACE_EMBEDDING,
            ProviderCapability.VISUAL_EMBEDDING,
            ProviderCapability.VLM,
        }:
            raise ValueError("unsupported visual HTTP capability")
        self.base_url = base_url.rstrip("/")
        self.capability = capability
        self.implementation = implementation
        self.version = version
        self.model = model
        self.code_license = code_license
        self.weight_license = weight_license
        self.model_checksum = model_checksum
        self.commercial_use_allowed = commercial_use_allowed

    def package(self) -> ProviderPackage:
        production = bool(
            self.weight_license and self.model_checksum and self.commercial_use_allowed
        )
        return ProviderPackage.model_validate(
            {
                "identity": {
                    "provider": self.implementation,
                    "implementation": "typed-json-http",
                    "version": self.version,
                    "model": self.model,
                    "checksum": self.model_checksum,
                    "license": f"{self.code_license}-code; weights-separate",
                },
                "capabilities": [self.capability],
                "admission": "production" if production else "research",
                "code_license": self.code_license,
                "weight_license": self.weight_license,
                "commercial_use_allowed": self.commercial_use_allowed,
                "model_checksum": self.model_checksum,
                "data_policy": {
                    "execution_location": "local",
                    "allowed_residencies": ["CN", "LOCAL"],
                    "transmits_source_media": False,
                    "retains_input": False,
                },
                "supported_hardware": ["cpu", "metal", "cuda"],
                "deterministic": False,
                "retry_safe": True,
                "max_batch_size": 32,
                "known_limitations": [
                    "Response must conform to NarratoPro typed visual JSON schema",
                    (
                        "Production admission requires exact code, weight, checksum "
                        "and benchmark approval"
                    ),
                ],
            }
        )

    @staticmethod
    def _paths(request: ProviderInvocationRequest) -> tuple[Path, ...]:
        values = request.parameters.get("frame_paths")
        if not isinstance(values, list) or not values:
            raise ValueError("visual HTTP request requires parameters.frame_paths")
        paths = tuple(
            Path(value).resolve(strict=True) for value in values if isinstance(value, str)
        )
        if len(paths) != len(values) or any(
            not path.is_file() or path.is_symlink() for path in paths
        ):
            raise ValueError("frame_paths must contain regular files")
        return paths

    def validate(self, request: ProviderInvocationRequest) -> None:
        if request.capability is not self.capability:
            raise ValueError("visual HTTP provider capability mismatch")
        self._paths(request)

    def estimate(self, request: ProviderInvocationRequest) -> ProviderResourceEstimate:
        paths = self._paths(request)
        total = sum(path.stat().st_size for path in paths)
        return ProviderResourceEstimate(
            cpu_cores=2,
            memory_bytes=2 * 1024**3,
            accelerator="metal",
            accelerator_memory_bytes=2 * 1024**3,
            temporary_disk_bytes=total,
            estimated_duration_ms=1_000 * len(paths),
        )

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.base_url}/health", timeout=2) as response:  # nosec B310
                return bool(response.status == 200)
        except (urllib.error.URLError, TimeoutError):
            return False

    def infer(self, request: ProviderInvocationRequest) -> ProviderRawOutput:
        started = time.perf_counter()
        payload = json.dumps(
            {
                "capability": self.capability.value,
                "frame_paths": [str(path) for path in self._paths(request)],
                "parameters": request.parameters,
            },
            separators=(",", ":"),
        ).encode()
        http_request = urllib.request.Request(  # nosec B310
            f"{self.base_url}/v1/visual/{self.capability.value}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(  # nosec B310
            http_request, timeout=request.timeout_ms / 1_000
        ) as response:
            raw = response.read()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("frames"), list):
            raise ValueError("visual provider response requires a frames array")
        duration = max(1, round((time.perf_counter() - started) * 1_000))
        return ProviderRawOutput(
            raw, "application/json", "narratopro-visual-response-v1", duration, 0
        )
