import pytest

from packages.evaluation import (
    character_error_rate,
    diarization_error_rate,
    edit_distance,
    entity_character_error_rate,
    jaccard_error_rate,
    mean_boundary_deviation_ms,
)


def test_character_error_rate_is_deterministic_and_keeps_negation_error() -> None:
    assert edit_distance(list("不答应"), list("答应")) == 1
    assert character_error_rate("我不答应", "我答应") == 0.25
    with pytest.raises(ValueError, match="must not be empty"):
        character_error_rate("", "text")


def test_timestamp_deviation_reports_mean_boundaries() -> None:
    assert mean_boundary_deviation_ms([(0.0, 1.0)], [(0.1, 1.2)]) == pytest.approx(150)
    with pytest.raises(ValueError, match="equal non-empty"):
        mean_boundary_deviation_ms([(0.0, 1.0)], [])


def test_entity_and_diarization_metrics_remain_separate() -> None:
    assert entity_character_error_rate(["游子"], ["柚子"]) == 0.5
    assert (
        diarization_error_rate(
            missed_seconds=1, false_alarm_seconds=1, confused_seconds=2, scored_seconds=10
        )
        == 0.4
    )
    assert jaccard_error_rate([{"a"}, {"a", "b"}], [{"a"}, {"b"}]) == 0.25
