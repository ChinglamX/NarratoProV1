from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import BenchmarkDataset, BenchmarkPrediction


def source_ref() -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": "SourceMedia"}


def case(case_id: str, series: str, split: str, gold: object = "hello") -> dict[str, object]:
    return {
        "case_id": case_id,
        "series_id": series,
        "episode_id": f"{series}-e1",
        "split": split,
        "source_ref": source_ref(),
        "slices": ["clean"],
        "annotation_guideline_version": "speech-v1",
        "gold": gold,
    }


def taxonomy() -> list[dict[str, object]]:
    return [
        {
            "error_id": "negation_flip",
            "capability": "asr",
            "severity": "S1",
            "description": "A negation changes meaning",
            "detection_rule_version": "v1",
        }
    ]


def test_benchmark_dataset_blocks_series_leakage_and_frozen_tuning() -> None:
    with pytest.raises(ValidationError, match="cross benchmark splits"):
        BenchmarkDataset.model_validate(
            {
                "dataset_id": "asr-v1",
                "version": "1",
                "capability": "asr",
                "cases": [
                    case("a", "series", "development"),
                    case("b", "series", "validation"),
                ],
                "taxonomy": taxonomy(),
            }
        )
    dataset = BenchmarkDataset.model_validate(
        {
            "dataset_id": "asr-v1",
            "version": "1",
            "capability": "asr",
            "cases": [case("frozen", "series", "frozen_test")],
            "taxonomy": taxonomy(),
        }
    )
    with pytest.raises(ValueError, match="prohibited for tuning"):
        dataset.assert_not_tuning_on_frozen_test(tuning=True)


def test_prediction_requires_exclusive_success_or_failure() -> None:
    base = {
        "case_id": "one",
        "provider": {
            "provider": "local",
            "implementation": "fake",
            "version": "1",
            "license": "Apache-2.0",
        },
        "raw_response_ref": None,
        "normalized_ref": None,
        "latency_ms": 1,
        "cost_micros": 0,
    }
    with pytest.raises(ValidationError, match="requires a value"):
        BenchmarkPrediction.model_validate(base)
    with pytest.raises(ValidationError, match="cannot claim"):
        BenchmarkPrediction.model_validate(
            base | {"value": "x", "failure_code": "provider_unavailable"}
        )
