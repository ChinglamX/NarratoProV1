"""Deterministic categorical baseline harness; capability metrics plug in separately."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from packages.contracts.benchmark import (
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkPrediction,
    SliceMetric,
)

SevereClassifier = Callable[[BenchmarkCase, BenchmarkPrediction], tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class BenchmarkSummary:
    metrics: tuple[SliceMetric, ...]
    severe_error_counts: dict[str, int]
    incomplete_case_ids: tuple[str, ...]


def summarize_exact_match(
    dataset: BenchmarkDataset,
    predictions: tuple[BenchmarkPrediction, ...],
    *,
    severe_classifier: SevereClassifier,
    metric_version: str = "exact-match-v1",
) -> BenchmarkSummary:
    cases = {case.case_id: case for case in dataset.cases}
    by_id = {prediction.case_id: prediction for prediction in predictions}
    if len(by_id) != len(predictions):
        raise ValueError("prediction case ids must be unique")
    unknown = sorted(set(by_id) - set(cases))
    if unknown:
        raise ValueError(f"predictions reference unknown cases: {', '.join(unknown)}")
    totals: dict[str, int] = defaultdict(int)
    matches: dict[str, int] = defaultdict(int)
    severe: Counter[str] = Counter()
    incomplete: list[str] = []
    for case in dataset.cases:
        prediction = by_id.get(case.case_id)
        if prediction is None or prediction.failure_code is not None:
            incomplete.append(case.case_id)
            continue
        detected = severe_classifier(case, prediction)
        allowed = {item.error_id for item in dataset.taxonomy}
        if not set(detected) <= allowed:
            raise ValueError("severe classifier emitted unknown taxonomy id")
        severe.update(detected)
        for slice_id in (*case.slices, "all"):
            totals[slice_id] += 1
            matches[slice_id] += int(prediction.value == case.gold)
    metrics = tuple(
        SliceMetric(
            metric="exact_match",
            metric_version=metric_version,
            slice_id=slice_id,
            numerator=matches[slice_id],
            denominator=denominator,
            value=matches[slice_id] / denominator,
        )
        for slice_id, denominator in sorted(totals.items())
    )
    if not metrics:
        raise ValueError("benchmark has no successful predictions to score")
    return BenchmarkSummary(metrics, dict(sorted(severe.items())), tuple(sorted(incomplete)))
