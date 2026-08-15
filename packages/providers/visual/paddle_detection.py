"""PaddleDetection RT-DETR provider adapter (E06 research; local runtime)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from packages.contracts import (
    ProviderCapability,
    ProviderInvocationRequest,
    ProviderPackage,
    ProviderResourceEstimate,
)
from packages.foundation.settings import get_settings
from packages.providers import ProviderRawOutput
from packages.providers.admission import CANDIDATE_VISUAL_PROVIDERS

_PROVIDER = "paddle-detection"
_MODEL_INSTANCE: Any | None = None


def _ensure_paddlex_cache() -> None:
    os.environ.setdefault(
        "PADDLE_PDX_CACHE_HOME",
        str(Path(get_settings().temp_root).parent / ".paddlex-cache"),
    )


def _registered_package() -> ProviderPackage:
    return next(
        p for p in CANDIDATE_VISUAL_PROVIDERS if p.identity.provider == _PROVIDER
    ).model_copy(deep=True)


class PaddleDetectionProvider:
    """Local RT-DETR-L (PaddleX) detector adapter; research admission only."""

    def package(self) -> ProviderPackage:
        return _registered_package()

    @staticmethod
    def _frame_path(request: ProviderInvocationRequest) -> Path:
        value = request.parameters.get("frame_path")
        if not isinstance(value, str):
            raise ValueError("PaddleDetection request requires parameters.frame_path")
        path = Path(value).resolve(strict=True)
        if not path.is_file() or path.is_symlink():
            raise ValueError("frame_path must be a regular file")
        return path

    def validate(self, request: ProviderInvocationRequest) -> None:
        if request.capability is not ProviderCapability.DETECTION:
            raise ValueError("PaddleDetection provider only supports DETECTION")
        self._frame_path(request)

    def estimate(self, request: ProviderInvocationRequest) -> ProviderResourceEstimate:
        size = self._frame_path(request).stat().st_size
        return ProviderResourceEstimate(
            cpu_cores=2,
            memory_bytes=1024**3,
            temporary_disk_bytes=size,
            estimated_duration_ms=2_000,
        )

    def health(self) -> bool:
        return True

    def infer(self, request: ProviderInvocationRequest) -> ProviderRawOutput:
        global _MODEL_INSTANCE
        _ensure_paddlex_cache()  # must precede any paddle import
        from paddlex import create_model  # type: ignore[import-untyped]  # lazy: research extra

        started = time.perf_counter()
        if _MODEL_INSTANCE is None:
            _MODEL_INSTANCE = create_model("RT-DETR-L")
        model = _MODEL_INSTANCE
        output = model.predict(str(self._frame_path(request)))
        detections: list[dict[str, object]] = []
        for page in output:
            boxes = page.get("boxes") or page.get("det_boxes") or []
            labels = page.get("labels") or page.get("det_labels") or []
            for index, box in enumerate(boxes):
                detections.append(
                    {
                        "label": labels[index] if index < len(labels) else "unknown",
                        "score": box.get("score"),
                        "region": {
                            "x_min": box.get("xmin"),
                            "y_min": box.get("ymin"),
                            "x_max": box.get("xmax"),
                            "y_max": box.get("ymax"),
                        },
                    }
                )
        payload = json.dumps(
            {"frames": [{"detections": detections}]}, separators=(",", ":")
        ).encode()
        elapsed = max(1, round((time.perf_counter() - started) * 1_000))
        return ProviderRawOutput(payload, "application/json", "paddlex-rtdetr-l-v1", elapsed, 0)
