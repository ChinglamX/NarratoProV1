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
from packages.providers.admission import CANDIDATE_PROVIDERS

_PROVIDER = "paddle-detection"
_MODEL_INSTANCE: Any | None = None


def _ensure_paddlex_cache() -> None:
    os.environ.setdefault(
        "PADDLE_PDX_CACHE_HOME",
        str(Path(get_settings().temp_root).parent / ".paddlex-cache"),
    )


def _registered_package() -> ProviderPackage:
    return next(p for p in CANDIDATE_PROVIDERS if p.identity.provider == _PROVIDER).model_copy(
        deep=True
    )


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
        import cv2
        from paddlex import create_model  # type: ignore[import-not-found]  # lazy: research extra

        started = time.perf_counter()
        path = self._frame_path(request)
        if _MODEL_INSTANCE is None:
            _MODEL_INSTANCE = create_model("RT-DETR-L")
        model = _MODEL_INSTANCE
        output = model.predict(str(path))
        image = cv2.imread(str(path))
        height, width = image.shape[:2] if image is not None else (1, 1)
        detections: list[dict[str, object]] = []
        for page in output:
            boxes = page.get("boxes") or page.get("det_boxes") or []
            page_labels = page.get("labels") or page.get("det_labels") or []
            for index, box in enumerate(boxes):
                region = _pixel_box_to_bbox(box, width, height)
                if region is None:
                    continue
                # PaddleX DetResult carries the label inside each box dict
                # (e.g. {"cls_id": 0, "label": "person", "score": ..., ...});
                # page-level labels are a legacy fallback.
                label = box.get("label") if isinstance(box, dict) else None
                if not label and index < len(page_labels):
                    label = page_labels[index]
                detections.append(
                    {
                        "label": label or "unknown",
                        "score": box.get("score"),
                        "region": region,
                    }
                )
        payload = json.dumps({"detections": detections}, separators=(",", ":")).encode()
        elapsed = max(1, round((time.perf_counter() - started) * 1_000))
        return ProviderRawOutput(payload, "application/json", "paddlex-rtdetr-l-v1", elapsed, 0)


def _pixel_box_to_bbox(box: Any, width: int, height: int) -> dict[str, float] | None:
    """Convert a PaddleX detection box to a normalized unit box.

    PaddleX boxes carry ``coordinate`` = [x1, y1, x2, y2] in pixels.
    """
    if width <= 0 or height <= 0:
        return None
    try:
        coordinate = box.get("coordinate")
        if not isinstance(coordinate, (list, tuple)) or len(coordinate) < 4:
            return None
        x_min, y_min, x_max, y_max = (float(value) for value in coordinate[:4])
    except (TypeError, ValueError, AttributeError):
        return None
    region = {
        "x_min": max(0.0, min(1.0, x_min / width)),
        "y_min": max(0.0, min(1.0, y_min / height)),
        "x_max": max(0.0, min(1.0, x_max / width)),
        "y_max": max(0.0, min(1.0, y_max / height)),
    }
    if region["x_max"] <= region["x_min"] or region["y_max"] <= region["y_min"]:
        return None
    return region
