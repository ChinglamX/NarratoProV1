from packages.longform.review import NarrationDraft, review_longform_narration


def line(**changes: object) -> NarrationDraft:
    values: dict[str, object] = {
        "line_id": "line-1",
        "chapter_id": "chapter-1",
        "text": "狼群退去后，真正压在兄妹身上的债务才刚刚出现。",  # noqa: RUF001
        "event_refs": ("debt",),
        "visual_event_refs": ("wolves-retreat",),
        "dialogue_excerpts": ("狼都退了",),
        "measured_duration_seconds": 4.0,
        "available_seconds": 8.0,
    }
    values.update(changes)
    return NarrationDraft(**values)  # type: ignore[arg-type]


def test_grounded_narration_passes() -> None:
    review = review_longform_narration((line(),))
    assert not review.blocked
    assert review.evidence_coverage == 1.0
    assert review.visual_alignment_coverage == 1.0


def test_missing_visual_evidence_and_overflow_block() -> None:
    review = review_longform_narration((line(visual_event_refs=(), measured_duration_seconds=9.0),))
    assert review.blocked
    assert {item.code for item in review.findings} >= {
        "missing-visual-evidence",
        "tts-duration-overflow",
    }


def test_high_dialogue_overlap_blocks() -> None:
    review = review_longform_narration(
        (line(text="这里面是五十万", dialogue_excerpts=("这里面是五十万现金",)),)
    )
    assert review.blocked
    assert "dialogue-overlap-high" in {item.code for item in review.findings}
