"""Deterministic G02 corpus and benchmark-harness acceptance."""

from __future__ import annotations

import json
from pathlib import Path

from packages.contracts import BenchmarkDataset, BenchmarkPrediction
from packages.evaluation import summarize_exact_match


def main() -> None:
    source = Path("evaluation/corpus/g02/asr_contract_fixture.json")
    dataset = BenchmarkDataset.model_validate_json(source.read_text(encoding="utf-8"))
    provider = {
        "provider": "fixture",
        "implementation": "deterministic",
        "version": "1",
        "license": "internal-test-only",
    }
    predictions = tuple(
        BenchmarkPrediction(
            case_id=case.case_id,
            provider=provider,
            value=case.gold if case.split != "frozen_test" else None,
            failure_code="provider_unavailable" if case.split == "frozen_test" else None,
            latency_ms=1,
            cost_micros=0,
        )
        for case in dataset.cases
    )
    summary = summarize_exact_match(
        dataset,
        predictions,
        severe_classifier=lambda *_: (),
    )
    print(
        json.dumps(
            {
                "cases": len(dataset.cases),
                "incomplete": list(summary.incomplete_case_ids),
                "metrics": len(summary.metrics),
                "series_isolated": True,
                "thresholds_declared": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
