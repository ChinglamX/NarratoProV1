"""Reproducible provider benchmark contracts with slice and severe-error lineage."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, JsonValue, model_validator

from packages.contracts.base import StrictContract
from packages.contracts.foundation import ArtifactRef, ProviderIdentity, StableName
from packages.contracts.providers import ProviderCapability, ProviderErrorCode


class BenchmarkSplit(StrEnum):
    DEVELOPMENT = "development"
    VALIDATION = "validation"
    FROZEN_TEST = "frozen_test"


class ErrorSeverity(StrEnum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class SevereErrorDefinition(StrictContract):
    error_id: StableName
    capability: ProviderCapability
    severity: ErrorSeverity
    description: Annotated[str, Field(min_length=1, max_length=2_048)]
    detection_rule_version: Annotated[str, Field(min_length=1, max_length=128)]


class BenchmarkCase(StrictContract):
    case_id: StableName
    series_id: StableName
    episode_id: StableName
    split: BenchmarkSplit
    source_ref: ArtifactRef
    slices: tuple[StableName, ...]
    annotation_guideline_version: Annotated[str, Field(min_length=1, max_length=128)]
    gold: JsonValue

    @model_validator(mode="after")
    def require_slices(self) -> Self:
        if not self.slices or len(self.slices) != len(set(self.slices)):
            raise ValueError("benchmark case requires unique slices")
        return self


class BenchmarkDataset(StrictContract):
    dataset_id: StableName
    version: Annotated[str, Field(min_length=1, max_length=128)]
    capability: ProviderCapability
    cases: tuple[BenchmarkCase, ...]
    taxonomy: tuple[SevereErrorDefinition, ...]

    @model_validator(mode="after")
    def prevent_leakage_and_duplicates(self) -> Self:
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark case ids must be unique")
        series_splits: dict[str, set[BenchmarkSplit]] = {}
        for case in self.cases:
            series_splits.setdefault(case.series_id, set()).add(case.split)
        leaked = sorted(series for series, splits in series_splits.items() if len(splits) > 1)
        if leaked:
            raise ValueError(f"series may not cross benchmark splits: {', '.join(leaked)}")
        taxonomy_ids = [item.error_id for item in self.taxonomy]
        if len(taxonomy_ids) != len(set(taxonomy_ids)):
            raise ValueError("severe error ids must be unique")
        if any(item.capability is not self.capability for item in self.taxonomy):
            raise ValueError("taxonomy capability must match dataset")
        return self

    def assert_not_tuning_on_frozen_test(self, *, tuning: bool) -> None:
        if tuning and any(case.split is BenchmarkSplit.FROZEN_TEST for case in self.cases):
            raise ValueError("frozen_test data is prohibited for tuning")


class BenchmarkPrediction(StrictContract):
    case_id: StableName
    provider: ProviderIdentity
    raw_response_ref: ArtifactRef | None = None
    normalized_ref: ArtifactRef | None = None
    value: JsonValue | None = None
    failure_code: ProviderErrorCode | None = None
    latency_ms: Annotated[int, Field(ge=0, le=2**63 - 1)]
    cost_micros: Annotated[int, Field(ge=0, le=2**63 - 1)]
    severe_error_ids: tuple[StableName, ...] = ()

    @model_validator(mode="after")
    def enforce_success_or_failure(self) -> Self:
        if self.failure_code is None and self.value is None:
            raise ValueError("successful prediction requires a value")
        if self.failure_code is not None and self.value is not None:
            raise ValueError("failed prediction cannot claim a value")
        if len(self.severe_error_ids) != len(set(self.severe_error_ids)):
            raise ValueError("severe error ids must be unique")
        return self


class SliceMetric(StrictContract):
    metric: StableName
    metric_version: Annotated[str, Field(min_length=1, max_length=128)]
    slice_id: StableName
    numerator: Annotated[int, Field(ge=0, le=2**63 - 1)]
    denominator: Annotated[int, Field(gt=0, le=2**63 - 1)]
    value: Annotated[float, Field(ge=0.0)]


class ProviderBenchmarkReport(StrictContract):
    dataset_ref: ArtifactRef
    prediction_set_ref: ArtifactRef
    provider: ProviderIdentity
    capability: ProviderCapability
    code_revision: Annotated[str, Field(min_length=1, max_length=128)]
    dependency_lock_checksum: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    hardware_profile: StableName
    seed: Annotated[int, Field(ge=0, le=2**63 - 1)]
    metrics: tuple[SliceMetric, ...]
    severe_error_counts: dict[StableName, Annotated[int, Field(ge=0)]]
    incomplete_case_ids: tuple[StableName, ...] = ()
    admission_thresholds_declared: bool = False

    @model_validator(mode="after")
    def require_metrics_and_no_implicit_threshold(self) -> Self:
        if not self.metrics:
            raise ValueError("benchmark report requires slice metrics")
        keys = [(item.metric, item.metric_version, item.slice_id) for item in self.metrics]
        if len(keys) != len(set(keys)):
            raise ValueError("slice metrics must be unique")
        return self
