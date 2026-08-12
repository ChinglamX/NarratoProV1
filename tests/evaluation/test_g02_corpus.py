from pathlib import Path

from packages.contracts import BenchmarkDataset


def test_g02_fixture_is_valid_series_isolated_and_not_a_quality_claim() -> None:
    dataset = BenchmarkDataset.model_validate_json(
        Path("evaluation/corpus/g02/asr_contract_fixture.json").read_text()
    )
    assert len({case.series_id for case in dataset.cases}) == len(dataset.cases)
    assert {case.split for case in dataset.cases} == {
        "development",
        "validation",
        "frozen_test",
    }
    assert "not production" in Path("evaluation/corpus/g02/README.md").read_text().lower()
