"""Versioned calibration-manifest contracts and leakage guards."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DatasetSplit(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    FROZEN_TEST = "frozen_test"


class UsagePurpose(StrEnum):
    EVALUATION = "evaluation"
    TUNING = "tuning"
    TRAINING = "training"


class RightsAndUsage(StrictModel):
    rights_status: Literal["approved", "restricted", "unknown"]
    allowed_purposes: frozenset[UsagePurpose]
    evidence_ref: str = Field(min_length=1)
    expires_at: datetime | None = None


class DatasetItem(StrictModel):
    item_id: str = Field(pattern=r"^[a-zA-Z0-9_.-]+$")
    series_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)
    split: DatasetSplit
    artifact_ref: str = Field(min_length=1)


class DatasetSplitManifest(StrictModel):
    manifest_id: str
    version: str
    items: tuple[DatasetItem, ...]

    @model_validator(mode="after")
    def prevent_series_leakage(self) -> DatasetSplitManifest:
        series_splits: dict[str, set[DatasetSplit]] = {}
        item_ids: set[str] = set()
        for item in self.items:
            if item.item_id in item_ids:
                raise ValueError(f"duplicate item_id: {item.item_id}")
            item_ids.add(item.item_id)
            series_splits.setdefault(item.series_id, set()).add(item.split)
        leaked = sorted(series for series, splits in series_splits.items() if len(splits) > 1)
        if leaked:
            raise ValueError(f"series may not cross dataset splits: {', '.join(leaked)}")
        return self

    def assert_usage(self, purpose: UsagePurpose) -> None:
        if purpose is UsagePurpose.TUNING and any(
            item.split is DatasetSplit.FROZEN_TEST for item in self.items
        ):
            raise ValueError("frozen_test data is prohibited for tuning")


class SliceDefinition(StrictModel):
    slice_id: str
    description: str
    selection_rule: str
    severity_focus: tuple[Literal["S0", "S1", "S2", "S3"], ...] = ()


class SliceCatalogManifest(StrictModel):
    version: str
    slices: tuple[SliceDefinition, ...]

    @model_validator(mode="after")
    def require_unique_slice_ids(self) -> SliceCatalogManifest:
        ids = [item.slice_id for item in self.slices]
        if len(ids) != len(set(ids)):
            raise ValueError("slice_id must be unique")
        return self


class GuidelineManifest(StrictModel):
    guideline_id: str
    version: str
    content_ref: str
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    frozen_at: datetime


class CalibrationPackManifest(StrictModel):
    pack_id: str
    version: str
    status: Literal["draft", "registered", "frozen", "deprecated"]
    dataset_manifest_ref: str
    guideline_refs: tuple[str, ...]
    slice_catalog_ref: str
    rights: RightsAndUsage
    created_at: datetime
    parent_pack_ref: str | None = None
