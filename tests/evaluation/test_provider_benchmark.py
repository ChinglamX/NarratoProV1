import pytest

from packages.contracts import BenchmarkDataset, BenchmarkPrediction
from packages.evaluation import summarize_exact_match
from tests.contracts.test_benchmark import case, taxonomy


def provider() -> dict[str, str]:
    return {
        "provider": "local",
        "implementation": "fake",
        "version": "1",
        "license": "Apache-2.0",
    }


def test_benchmark_summary_is_slice_aware_and_tracks_incomplete_and_severe() -> None:
    dataset = BenchmarkDataset.model_validate(
        {
            "dataset_id": "asr-v1",
            "version": "1",
            "capability": "asr",
            "cases": [
                case("ok", "series-a", "validation", "yes"),
                case("wrong", "series-b", "validation", "not"),
                case("missing", "series-c", "validation", "hello"),
            ],
            "taxonomy": taxonomy(),
        }
    )
    predictions = (
        BenchmarkPrediction(
            case_id="ok", provider=provider(), value="yes", latency_ms=1, cost_micros=0
        ),
        BenchmarkPrediction(
            case_id="wrong", provider=provider(), value="yes", latency_ms=2, cost_micros=0
        ),
        BenchmarkPrediction(
            case_id="missing",
            provider=provider(),
            failure_code="provider_unavailable",
            latency_ms=0,
            cost_micros=0,
        ),
    )
    result = summarize_exact_match(
        dataset,
        predictions,
        severe_classifier=lambda item, _prediction: (
            ("negation_flip",) if item.case_id == "wrong" else ()
        ),
    )
    overall = next(metric for metric in result.metrics if metric.slice_id == "all")
    assert overall.value == 0.5
    assert result.severe_error_counts == {"negation_flip": 1}
    assert result.incomplete_case_ids == ("missing",)


def test_benchmark_rejects_unknown_prediction_and_taxonomy_output() -> None:
    dataset = BenchmarkDataset.model_validate(
        {
            "dataset_id": "asr-v1",
            "version": "1",
            "capability": "asr",
            "cases": [case("one", "series", "validation")],
            "taxonomy": taxonomy(),
        }
    )
    unknown = BenchmarkPrediction(
        case_id="other", provider=provider(), value="x", latency_ms=1, cost_micros=0
    )
    with pytest.raises(ValueError, match="unknown cases"):
        summarize_exact_match(dataset, (unknown,), severe_classifier=lambda *_: ())
    valid = unknown.model_copy(update={"case_id": "one"})
    with pytest.raises(ValueError, match="unknown taxonomy"):
        summarize_exact_match(dataset, (valid,), severe_classifier=lambda *_: ("invented",))
