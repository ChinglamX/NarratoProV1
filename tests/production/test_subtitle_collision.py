"""E10/K05 subtitle collision detection unit tests."""

from uuid import uuid4

from packages.contracts.media_production import SubtitleCue
from packages.production.subtitle_collision import detect_subtitle_collisions


def _cue(start_us: int, duration_us: int, *, safe: dict | None = None) -> SubtitleCue:
    return SubtitleCue(
        cue_id=uuid4(),
        line_id=uuid4(),
        timeline_range={
            "start": {"value": start_us, "rate_num": 1_000_000},
            "duration": {"value": duration_us, "rate_num": 1_000_000},
        },
        text="字幕文本",
        style_ref="primary",
        safe_area=safe or {"y": 0.8, "height": 0.14},
    )


def test_no_collisions_for_sequential_cues() -> None:
    cues = (_cue(0, 4_000_000), _cue(4_000_000, 5_000_000))
    assert detect_subtitle_collisions(cues) == ()


def test_detects_temporal_overlap() -> None:
    a = _cue(0, 4_000_000)
    b = _cue(3_000_000, 5_000_000)
    findings = detect_subtitle_collisions((a, b))
    assert any(f"temporal-overlap:{a.cue_id}" in f for f in findings)


def test_detects_safe_area_violation() -> None:
    cue = _cue(0, 1_000_000, safe={"y": 0.9, "height": 0.2})  # bottom exceeds 1.0
    findings = detect_subtitle_collisions((cue,))
    assert any(f"safe-area-violation:{cue.cue_id}" in f for f in findings)


def test_findings_are_deterministic_and_ordered() -> None:
    a = _cue(0, 4_000_000)
    b = _cue(3_000_000, 5_000_000, safe={"y": 1.0, "height": 0.5})
    first = detect_subtitle_collisions((a, b))
    second = detect_subtitle_collisions((b, a))  # input order must not matter
    assert first == second
    assert first == tuple(sorted(first))
    assert first
