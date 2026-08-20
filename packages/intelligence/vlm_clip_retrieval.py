"""Research VLM-driven clip window retrieval (auto clip selection).

Mechanism: for a Story event, sample source frames, ask a VLM whether each
frame shows the event's content, deterministically parse the verdicts, and
merge contiguous relevant frames into candidate source windows. The produced
windows become ``ClipCandidate`` entries with evidence refs.

This is a *research* path: the VLM is non-deterministic and not
production-admitted, so candidates carry explicit provenance and confidence
must stay ``unavailable`` until calibrated; downstream human review (the E09
timeline checkpoint) is mandatory. The parse and window selection here are
pure, deterministic and unit-testable given the VLM verdicts.
"""

from __future__ import annotations

from dataclasses import dataclass

RELEVANT_MARKER = "相关"
IRRELEVANT_MARKER = "不相关"


@dataclass(frozen=True, slots=True)
class FrameRelevance:
    """Parsed VLM verdict for one sampled frame."""

    frame_seconds: float
    relevant: bool
    raw_verdict: str


def parse_relevance_verdict(verdict: str) -> bool:
    """Deterministically parse a VLM relevance verdict.

    The prompt asks the model to answer only 相关 or 不相关. We accept the
    explicit positive token and fail closed (treated as irrelevant) on any
    ambiguous or empty output, so a noisy model never fabricates relevance.
    """
    normalized = (verdict or "").strip().lower()
    has_positive = RELEVANT_MARKER in normalized
    has_negative = IRRELEVANT_MARKER in normalized
    if has_negative:
        return False
    return has_positive


def select_relevant_windows(
    frames: list[FrameRelevance],
    *,
    max_gap_seconds: float = 3.0,
    minimum_window_seconds: float = 2.0,
) -> list[tuple[float, float]]:
    """Merge contiguous relevant frames into source windows.

    Two relevant runs separated by at most ``max_gap_seconds`` of irrelevant
    frames merge into one window; runs shorter than ``minimum_window_seconds``
    are dropped. Input frames must be sorted by ``frame_seconds``. The result
    is deterministic for the same verdicts.
    """
    ordered = sorted(frames, key=lambda item: item.frame_seconds)
    runs: list[list[FrameRelevance]] = []
    for frame in ordered:
        if frame.relevant:
            if runs and frame.frame_seconds - runs[-1][-1].frame_seconds <= max_gap_seconds:
                runs[-1].append(frame)
            else:
                runs.append([frame])
    windows: list[tuple[float, float]] = []
    for run in runs:
        start = run[0].frame_seconds
        end = run[-1].frame_seconds
        if end - start >= minimum_window_seconds:
            windows.append((start, end))
    return windows


def relevance_ratio(frames: list[FrameRelevance]) -> float:
    """Fraction of sampled frames judged relevant (evidence score source)."""
    if not frames:
        return 0.0
    return sum(1 for item in frames if item.relevant) / len(frames)


def refine_evidence_window(
    frames: list[FrameRelevance],
    evidence_window: tuple[float, float],
    *,
    max_gap_seconds: float = 3.0,
    minimum_window_seconds: float = 2.0,
) -> tuple[float, float]:
    """Refine an evidence window with VLM verdicts (evidence-first + re-rank).

    Given an evidence window (e.g. an ASR/Story-derived source range), keep
    only the frames inside it, merge contiguous relevant runs (gaps up to
    ``max_gap_seconds``), and return the run with the most relevant frames
    (earliest start breaks ties). If no frame inside the window is relevant,
    the evidence window itself is returned unchanged (fail-open to evidence,
    never an empty window).
    """
    start, end = evidence_window
    inside = [item for item in frames if start - 1e-9 <= item.frame_seconds <= end + 1e-9]
    if not any(item.relevant for item in inside):
        return (start, end)
    runs: list[list[FrameRelevance]] = []
    for frame in sorted(inside, key=lambda item: item.frame_seconds):
        if not frame.relevant:
            continue
        if runs and frame.frame_seconds - runs[-1][-1].frame_seconds <= max_gap_seconds:
            runs[-1].append(frame)
        else:
            runs.append([frame])
    usable = [
        run
        for run in runs
        if run[-1].frame_seconds - run[0].frame_seconds >= minimum_window_seconds
    ]
    if not usable:
        return (start, end)
    best = max(
        usable,
        key=lambda run: (
            sum(1 for item in run if item.relevant),
            -run[0].frame_seconds,
        ),
    )
    return (best[0].frame_seconds, best[-1].frame_seconds)
