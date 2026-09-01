"""Unit tests for research VLM clip window retrieval."""

# ruff: noqa: RUF001 - CJK verdict strings are intentional

from packages.intelligence.vlm_clip_retrieval import (
    FrameRelevance,
    parse_relevance_verdict,
    refine_evidence_window,
    relevance_ratio,
    select_relevant_windows,
)


def test_parse_explicit_positive() -> None:
    assert parse_relevance_verdict("相关") is True
    assert parse_relevance_verdict("画面与事件相关。") is True


def test_parse_negative_wins_over_ambiguous() -> None:
    assert parse_relevance_verdict("不相关") is False
    assert parse_relevance_verdict("画面与事件不相关，是风景。") is False


def test_parse_fails_closed_on_ambiguous_or_empty() -> None:
    assert parse_relevance_verdict("不确定") is False
    assert parse_relevance_verdict("") is False
    assert parse_relevance_verdict(None) is False  # type: ignore[arg-type]


def _frames(pairs: list[tuple[float, bool]]) -> list[FrameRelevance]:
    return [
        FrameRelevance(frame_seconds=seconds, relevant=flag, raw_verdict="")
        for seconds, flag in pairs
    ]


def test_windows_merge_short_gaps_and_drop_short_runs() -> None:
    frames = _frames(
        [
            (1.0, True),
            (3.0, True),
            (5.0, False),  # one irrelevant frame; gap 6-3=3s <= 3s -> merged
            (6.0, True),
            (9.0, True),
            (30.0, True),  # isolated short run (30-30 < 2s min) -> dropped
        ]
    )
    windows = select_relevant_windows(frames)
    assert windows == [(1.0, 9.0)]


def test_windows_split_on_long_gap() -> None:
    frames = _frames([(1.0, True), (3.0, True), (20.0, True), (22.0, True)])
    windows = select_relevant_windows(frames, max_gap_seconds=3.0)
    assert windows == [(1.0, 3.0), (20.0, 22.0)]


def test_windows_deterministic_given_verdicts() -> None:
    frames = _frames([(2.0, True), (4.0, False), (6.0, True), (8.0, True)])
    first = select_relevant_windows(frames)
    second = select_relevant_windows(list(reversed(frames)))
    assert first == second


def test_relevance_ratio() -> None:
    frames = _frames([(1.0, True), (2.0, False), (3.0, True)])
    assert relevance_ratio(frames) == 2 / 3
    assert relevance_ratio([]) == 0.0


def test_refine_keeps_best_relevant_run_inside_evidence_window() -> None:
    frames = _frames(
        [
            (1.0, True),
            (3.0, True),
            (5.0, True),
            (10.0, False),
            (12.0, True),
            (14.0, True),
            (40.0, True),  # outside the evidence window -> ignored
        ]
    )
    refined = refine_evidence_window(frames, (0.0, 20.0))
    assert refined == (1.0, 5.0)  # 3 relevant frames beats the 2-frame run


def test_refine_fails_open_to_evidence_when_no_relevant_frame() -> None:
    frames = _frames([(1.0, False), (3.0, False), (5.0, False)])
    assert refine_evidence_window(frames, (2.0, 6.0)) == (2.0, 6.0)


def test_refine_ignores_frames_outside_evidence_window() -> None:
    frames = _frames([(1.0, True), (2.0, True), (9.0, True), (11.0, True)])
    assert refine_evidence_window(frames, (5.0, 12.0)) == (9.0, 11.0)


def test_refine_short_run_falls_back_to_evidence() -> None:
    frames = _frames([(1.0, True), (2.0, True), (9.0, True), (10.0, True)])
    assert refine_evidence_window(frames, (5.0, 12.0)) == (5.0, 12.0)


def test_refine_deterministic_given_verdicts() -> None:
    frames = _frames([(2.0, True), (4.0, True), (6.0, False), (8.0, True), (10.0, True)])
    first = refine_evidence_window(frames, (0.0, 12.0))
    second = refine_evidence_window(list(reversed(frames)), (0.0, 12.0))
    assert first == second
