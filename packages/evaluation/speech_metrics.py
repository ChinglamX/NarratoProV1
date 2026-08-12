"""Versioned deterministic Speech metrics used by G03 benchmarks."""

from __future__ import annotations

from collections.abc import Sequence


def edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, actual in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + int(expected != actual),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    expected = list(reference.replace(" ", ""))
    actual = list(hypothesis.replace(" ", ""))
    if not expected:
        raise ValueError("CER reference must not be empty")
    return edit_distance(expected, actual) / len(expected)


def entity_character_error_rate(
    reference_entities: Sequence[str], hypothesis_entities: Sequence[str]
) -> float:
    if not reference_entities:
        raise ValueError("entity CER requires at least one reference entity")
    reference = "|".join(reference_entities)
    hypothesis = "|".join(hypothesis_entities)
    return character_error_rate(reference, hypothesis)


def diarization_error_rate(
    *,
    missed_seconds: float,
    false_alarm_seconds: float,
    confused_seconds: float,
    scored_seconds: float,
) -> float:
    if scored_seconds <= 0 or min(missed_seconds, false_alarm_seconds, confused_seconds) < 0:
        raise ValueError("DER inputs require positive scored time and non-negative errors")
    return (missed_seconds + false_alarm_seconds + confused_seconds) / scored_seconds


def jaccard_error_rate(
    reference_speakers: Sequence[set[str]], hypothesis_speakers: Sequence[set[str]]
) -> float:
    if not reference_speakers or len(reference_speakers) != len(hypothesis_speakers):
        raise ValueError("JER requires equal non-empty speaker frames")
    errors = []
    for expected, actual in zip(reference_speakers, hypothesis_speakers, strict=True):
        union = expected | actual
        errors.append(0.0 if not union else 1.0 - len(expected & actual) / len(union))
    return sum(errors) / len(errors)


def mean_boundary_deviation_ms(
    reference: Sequence[tuple[float, float]],
    hypothesis: Sequence[tuple[float, float]],
) -> float:
    if not reference or len(reference) != len(hypothesis):
        raise ValueError("timestamp metric requires equal non-empty boundary sets")
    total = sum(
        abs(expected_start - actual_start) + abs(expected_end - actual_end)
        for (expected_start, expected_end), (actual_start, actual_end) in zip(
            reference, hypothesis, strict=True
        )
    )
    return total * 1000 / (2 * len(reference))
