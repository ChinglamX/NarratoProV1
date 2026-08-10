from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from packages.contracts.calibration import (
    CalibrationPackManifest,
    DatasetItem,
    DatasetSplit,
    DatasetSplitManifest,
    SliceCatalogManifest,
    UsagePurpose,
)


def item(item_id: str, series: str, split: DatasetSplit) -> DatasetItem:
    return DatasetItem(
        item_id=item_id,
        series_id=series,
        episode_id=f"{series}-e01",
        split=split,
        artifact_ref=f"artifact:{item_id}",
    )


def test_rejects_series_crossing_splits() -> None:
    with pytest.raises(ValidationError, match="series may not cross"):
        DatasetSplitManifest(
            manifest_id="m1",
            version="1.0.0",
            items=(
                item("a", "series-1", DatasetSplit.TRAIN),
                item("b", "series-1", DatasetSplit.FROZEN_TEST),
            ),
        )


def test_frozen_test_cannot_be_used_for_tuning() -> None:
    manifest = DatasetSplitManifest(
        manifest_id="m1",
        version="1.0.0",
        items=(item("a", "series-1", DatasetSplit.FROZEN_TEST),),
    )
    with pytest.raises(ValueError, match="prohibited for tuning"):
        manifest.assert_usage(UsagePurpose.TUNING)


def test_manifest_is_immutable() -> None:
    manifest = DatasetSplitManifest(manifest_id="m1", version="1", items=())
    with pytest.raises(ValidationError):
        manifest.version = datetime.now(UTC).isoformat()  # type: ignore[misc]


def test_bootstrap_registry_manifests_are_valid() -> None:
    root = Path("benchmarks/manifests")
    CalibrationPackManifest.model_validate(
        yaml.safe_load((root / "calibration_pack_v1.yaml").read_text())
    )
    DatasetSplitManifest.model_validate(
        yaml.safe_load((root / "dataset_split_v1.yaml").read_text())
    )
    SliceCatalogManifest.model_validate(
        yaml.safe_load((root / "slice_catalog_v1.yaml").read_text())
    )
