"""PaddleOCR provider adapter (E06 research; PP-OCRv6 local runtime)."""

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

_PROVIDER = "paddleocr"
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


class PaddleOCRProvider:
    """Local PaddleOCR (PP-OCRv6) adapter; research admission only.

    Heavy paddle imports happen lazily inside ``infer`` so the core install
    (without the ``research`` extra) still imports this module cleanly.
    """

    def package(self) -> ProviderPackage:
        return _registered_package()

    @staticmethod
    def _frame_path(request: ProviderInvocationRequest) -> Path:
        value = request.parameters.get("frame_path")
        if not isinstance(value, str):
            raise ValueError("PaddleOCR request requires parameters.frame_path")
        path = Path(value).resolve(strict=True)
        if not path.is_file() or path.is_symlink():
            raise ValueError("frame_path must be a regular file")
        return path

    def validate(self, request: ProviderInvocationRequest) -> None:
        if request.capability is not ProviderCapability.OCR:
            raise ValueError("PaddleOCR provider only supports OCR")
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
        from paddleocr import PaddleOCR  # type: ignore[import-untyped]  # lazy: research extra

        started = time.perf_counter()
        if _MODEL_INSTANCE is None:
            _MODEL_INSTANCE = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        ocr = _MODEL_INSTANCE
        result = ocr.predict(str(self._frame_path(request)))
        page = result[0]
        texts = list(page.get("rec_texts", []))
        scores = [
            float(score) if score is not None else None for score in page.get("rec_scores", [])
        ]
        polys = [
            poly.tolist() if hasattr(poly, "tolist") else poly for poly in page.get("rec_polys", [])
        ]
        frames = [
            {
                "ocr_texts": texts,
                "ocr_scores": scores,
                "regions": polys,
            }
        ]
        payload = json.dumps({"frames": frames}, separators=(",", ":")).encode()
        elapsed = max(1, round((time.perf_counter() - started) * 1_000))
        return ProviderRawOutput(payload, "application/json", "paddleocr-ppocrv6-v1", elapsed, 0)
