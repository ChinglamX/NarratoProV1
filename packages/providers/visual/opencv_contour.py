"""Pinned OpenCV 5.0.0 contour-candidate detector and frame-quality output."""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2

from packages.contracts import ProviderInvocationRequest, ProviderPackage, ProviderResourceEstimate
from packages.providers import ProviderRawOutput


class OpenCVContourProvider:
    def package(self) -> ProviderPackage:
        return ProviderPackage.model_validate(
            {
                "identity": {
                    "provider": "opencv",
                    "implementation": "contour-candidate-detector",
                    "version": "5.0.0.93",
                    "license": "Apache-2.0-code",
                },
                "capabilities": ["detection"],
                "admission": "research",
                "code_license": "Apache-2.0",
                "weight_license": None,
                "commercial_use_allowed": False,
                "model_checksum": None,
                "data_policy": {
                    "execution_location": "local",
                    "allowed_residencies": ["CN", "LOCAL"],
                    "transmits_source_media": False,
                    "retains_input": False,
                },
                "supported_hardware": ["cpu"],
                "deterministic": True,
                "retry_safe": True,
                "max_batch_size": 1,
                "known_limitations": [
                    "Contours are generic foreground candidates, not semantic person identity",
                    "This is an engineering baseline, not the production detector",
                ],
            }
        )

    @staticmethod
    def _path(request: ProviderInvocationRequest) -> Path:
        value = request.parameters.get("frame_path")
        if not isinstance(value, str):
            raise ValueError("OpenCV request requires parameters.frame_path")
        path = Path(value).resolve(strict=True)
        if not path.is_file() or path.is_symlink():
            raise ValueError("frame_path must be a regular file")
        return path

    def validate(self, request: ProviderInvocationRequest) -> None:
        if request.capability.value != "detection":
            raise ValueError("OpenCV contour provider only supports detection")
        self._path(request)

    def estimate(self, request: ProviderInvocationRequest) -> ProviderResourceEstimate:
        size = self._path(request).stat().st_size
        return ProviderResourceEstimate(
            cpu_cores=2,
            memory_bytes=512 * 1024**2,
            temporary_disk_bytes=size,
            estimated_duration_ms=1_000,
        )

    def health(self) -> bool:
        return True

    def infer(self, request: ProviderInvocationRequest) -> ProviderRawOutput:
        started = time.perf_counter()
        image = cv2.imread(str(self._path(request)))
        if image is None or image.size == 0:
            raise ValueError("OpenCV could not decode frame")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        height, width = image.shape[:2]
        detections = [
            {
                "label": "foreground-region",
                "region": {
                    "x_min": x / width,
                    "y_min": y / height,
                    "x_max": (x + box_width) / width,
                    "y_max": (y + box_height) / height,
                },
                "score": min(1.0, box_width * box_height / (width * height)),
            }
            for contour in contours
            for x, y, box_width, box_height in [cv2.boundingRect(contour)]
            if 0.01 <= box_width * box_height / (width * height) < 0.95
        ]
        mean = float(gray.mean()) / 255
        contrast = min(1.0, float(gray.std()) / 128)
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        payload = json.dumps(
            {
                "detections": detections,
                "quality": {
                    "blur_score": blur,
                    "mean_luminance": mean,
                    "contrast": contrast,
                    "usable_for_identity": blur >= 50 and 0.1 <= mean <= 0.9,
                },
            },
            separators=(",", ":"),
        ).encode()
        elapsed = max(1, round((time.perf_counter() - started) * 1_000))
        return ProviderRawOutput(payload, "application/json", "opencv-hog-frame-v1", elapsed, 0)
