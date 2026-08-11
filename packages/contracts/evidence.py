"""Canonical evidence and confidence contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, JsonValue, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import UUID, ArtifactRef, StableName, TimeRange


class EvidenceType(StrEnum):
    DIALOGUE = "dialogue"
    VISUAL = "visual"
    OCR = "ocr"
    AUDIO = "audio"
    METADATA = "metadata"
    HUMAN_NOTE = "human_note"


class FrameRange(StrictContract):
    """Half-open frame interval within the referenced source artifact."""

    start_frame: Annotated[int, Field(ge=0, le=2**63 - 1)]
    end_frame: Annotated[int, Field(ge=1, le=2**63 - 1)]

    @model_validator(mode="after")
    def require_non_empty_ordered_range(self) -> Self:
        if self.end_frame <= self.start_frame:
            raise ValueError("end_frame must be greater than start_frame")
        return self


class EvidenceLink(StrictContract):
    """Traceable pointer from a conclusion to exact source evidence."""

    evidence_id: UUID
    source: ArtifactRef
    source_range: TimeRange | None = None
    frame_range: FrameRange | None = None
    evidence_type: EvidenceType
    excerpt: Annotated[str, Field(min_length=1, max_length=4_096)] | None = None


class ConfidenceStatus(StrEnum):
    SHADOW = "shadow"
    CALIBRATED = "calibrated"
    UNAVAILABLE = "unavailable"
    DRIFTED = "drifted"


class RiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConfidenceFactor(StrictContract):
    """One explainable factor supporting or opposing a confidence estimate."""

    code: StableName
    description: Annotated[str, Field(min_length=1, max_length=1_024)]
    value: JsonValue | None = None


class ConfidenceRecord(StrictContract):
    """Scoped confidence estimate; never an authorization to auto-release."""

    score: Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)] | None
    status: ConfidenceStatus
    method: Annotated[str, Field(min_length=1, max_length=255)]
    calibration_version: Annotated[str, Field(min_length=1, max_length=128)] | None = None
    applicable_scope: Annotated[str, Field(min_length=1, max_length=512)]
    risk_class: RiskClass
    supporting_factors: tuple[ConfidenceFactor, ...] = ()
    opposing_factors: tuple[ConfidenceFactor, ...] = ()
    evidence: tuple[EvidenceLink, ...] = ()

    @model_validator(mode="after")
    def enforce_status_semantics(self) -> Self:
        if self.status is ConfidenceStatus.UNAVAILABLE:
            if self.score is not None:
                raise ValueError("unavailable confidence must not include a score")
            if self.calibration_version is not None:
                raise ValueError("unavailable confidence must not claim calibration")
            return self
        if self.score is None:
            raise ValueError(f"{self.status.value} confidence requires a score")
        if self.status is ConfidenceStatus.CALIBRATED and self.calibration_version is None:
            raise ValueError("calibrated confidence requires calibration_version")
        if self.status is ConfidenceStatus.DRIFTED and self.calibration_version is None:
            raise ValueError("drifted confidence requires calibration_version")
        if self.status is ConfidenceStatus.SHADOW and self.calibration_version is not None:
            raise ValueError("shadow confidence must not claim a production calibration")
        return self
