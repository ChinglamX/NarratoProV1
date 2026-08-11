"""Shadow-only prediction/correction examples; never used for routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ShadowPrediction:
    module: str
    prediction: dict[str, Any]
    confidence: dict[str, Any]
    model_version: str | None
    prompt_version: str | None
    config_version: str | None

    @property
    def complete(self) -> bool:
        return all((self.model_version, self.prompt_version, self.config_version))

    def calibration_example(
        self,
        *,
        corrected: dict[str, Any],
        reviewer_id: str,
        review_duration_ms: int,
    ) -> dict[str, Any]:
        return {
            "module": self.module,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "corrected": corrected,
            "reviewer_id": reviewer_id,
            "review_duration_ms": review_duration_ms,
            "versions": {
                "model": self.model_version,
                "prompt": self.prompt_version,
                "config": self.config_version,
            },
            "status": "complete" if self.complete else "incomplete",
            "routing_authority": False,
        }
