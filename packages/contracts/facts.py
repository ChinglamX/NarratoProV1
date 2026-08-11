"""Canonical observation-grounded fact and evidence-bundle contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import Field, JsonValue, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.evidence import ConfidenceRecord, EvidenceLink
from packages.contracts.foundation import UUID, ArtifactRef, ProviderIdentity, StableName, TimeRange


class FactType(StrEnum):
    DIALOGUE = "dialogue"
    SPEAKER = "speaker"
    PERSON = "person"
    ENTITY = "entity"
    OCR = "ocr"
    ACTION = "action"
    VISUAL_SIGNAL = "visual_signal"
    AUDIO_SIGNAL = "audio_signal"


class FactStatus(StrEnum):
    OBSERVED = "observed"
    DISPUTED = "disputed"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"


class Fact(StrictContract):
    """Observable claim only; motivation, causality, and semantic emotion are Story."""

    fact_id: UUID
    fact_type: FactType
    subject_ref: StableName | None = None
    value: JsonValue
    source_range: TimeRange
    evidence: tuple[EvidenceLink, ...]
    provider: ProviderIdentity
    confidence: ConfidenceRecord
    status: FactStatus

    @model_validator(mode="after")
    def require_grounding(self) -> Self:
        if not self.evidence:
            raise ValueError("fact requires at least one evidence link")
        if self.source_range.is_empty:
            raise ValueError("fact source range must be non-empty")
        return self


class FactSet(StrictContract):
    source_refs: tuple[ArtifactRef, ...]
    facts: tuple[Fact, ...]
    incomplete: bool = False
    unavailable_partitions: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def require_unique_fact_ids(self) -> Self:
        ids = [item.fact_id for item in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("fact ids must be unique")
        if self.unavailable_partitions and not self.incomplete:
            raise ValueError("unavailable partitions require incomplete=true")
        return self


class EvidenceBundle(StrictContract):
    target_ref: ArtifactRef
    links: tuple[EvidenceLink, ...]

    @model_validator(mode="after")
    def require_unique_evidence_ids(self) -> Self:
        ids = [item.evidence_id for item in self.links]
        if len(ids) != len(set(ids)):
            raise ValueError("evidence ids must be unique")
        return self


class QualityFeatureStatus(StrEnum):
    MEASURED = "measured"
    UNAVAILABLE = "unavailable"


class SourceQualityFeature(StrictContract):
    feature_id: UUID
    source: ArtifactRef
    source_range: TimeRange
    metric: StableName
    method: StableName
    profile_ref: ArtifactRef
    status: QualityFeatureStatus
    value: JsonValue | None = None
    unit: StableName | None = None

    @model_validator(mode="after")
    def enforce_measurement_status(self) -> Self:
        if self.status is QualityFeatureStatus.MEASURED and self.value is None:
            raise ValueError("measured quality feature requires a value")
        if self.status is QualityFeatureStatus.UNAVAILABLE and self.value is not None:
            raise ValueError("unavailable quality feature cannot claim a value")
        return self


class SourceQualityFeatureSet(StrictContract):
    source: ArtifactRef
    features: tuple[SourceQualityFeature, ...] = Field(default=())

    @model_validator(mode="after")
    def require_consistent_source(self) -> Self:
        if any(item.source != self.source for item in self.features):
            raise ValueError("all quality features must reference the set source")
        return self
