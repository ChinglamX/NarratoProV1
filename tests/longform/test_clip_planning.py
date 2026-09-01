from packages.longform.clip_planning import CandidateShot, plan_chapter_clips
from packages.longform.planning import Chapter, ChapterBlueprint, ChapterFunction


def blueprint(*, protected: bool = False) -> ChapterBlueprint:
    return ChapterBlueprint(
        arc_id="arc",
        target_seconds=10,
        chapters=(
            Chapter(
                chapter_id="chapter-1",
                function=ChapterFunction.CONFLICT,
                event_refs=("conflict",),
                target_seconds=10,
                narration_budget_seconds=5,
                protects_original_audio=protected,
            ),
        ),
        findings=(),
    )


def shot(name: str, duration: float, *, protected: bool = False) -> CandidateShot:
    return CandidateShot(
        shot_id=name,
        source_path="episode-1.mp4",
        episode=1,
        start_seconds=1,
        duration_seconds=duration,
        event_refs=("conflict",),
        visual_score=0.8,
        continuity_group="scene-a",
        contains_protected_audio=protected,
    )


def test_unique_shots_fill_chapter_without_duplication() -> None:
    plan = plan_chapter_clips(
        blueprint=blueprint(),
        shots=(shot("a", 6), shot("b", 6)),
        minimum_chapter_coverage=1,
    )
    assert not plan.blocked
    assert plan.selected_seconds == 10
    assert {item.shot_id for item in plan.selected} == {"a", "b"}


def test_insufficient_media_and_missing_original_audio_block() -> None:
    plan = plan_chapter_clips(
        blueprint=blueprint(protected=True),
        shots=(shot("a", 3),),
    )
    assert plan.blocked
    assert {item.code for item in plan.findings} == {
        "insufficient-unique-media-coverage",
        "missing-protected-original-audio-shot",
    }


def test_selection_rank_does_not_override_causal_or_source_order() -> None:
    ordered_blueprint = ChapterBlueprint(
        arc_id="arc",
        target_seconds=4,
        chapters=(
            Chapter(
                chapter_id="chapter-1",
                function=ChapterFunction.CONFLICT,
                event_refs=("setup", "consequence"),
                target_seconds=4,
                narration_budget_seconds=2,
                protects_original_audio=False,
            ),
        ),
        findings=(),
    )
    candidates = (
        CandidateShot(
            shot_id="consequence-high-score",
            source_path="episode-1.mp4",
            episode=1,
            start_seconds=20,
            duration_seconds=1,
            event_refs=("consequence",),
            visual_score=1,
        ),
        CandidateShot(
            shot_id="setup-later",
            source_path="episode-1.mp4",
            episode=1,
            start_seconds=12,
            duration_seconds=1,
            event_refs=("setup",),
            visual_score=0.8,
        ),
        CandidateShot(
            shot_id="setup-earlier",
            source_path="episode-1.mp4",
            episode=1,
            start_seconds=10,
            duration_seconds=1,
            event_refs=("setup",),
            visual_score=0.7,
        ),
        CandidateShot(
            shot_id="consequence-low-score",
            source_path="episode-1.mp4",
            episode=1,
            start_seconds=21,
            duration_seconds=1,
            event_refs=("consequence",),
            visual_score=0.6,
        ),
    )

    plan = plan_chapter_clips(
        blueprint=ordered_blueprint,
        shots=candidates,
        minimum_chapter_coverage=1,
    )

    assert [item.shot_id for item in plan.selected] == [
        "setup-earlier",
        "setup-later",
        "consequence-high-score",
        "consequence-low-score",
    ]


def test_flash_frame_candidates_are_not_used_as_story_clips() -> None:
    plan = plan_chapter_clips(
        blueprint=blueprint(),
        shots=(shot("flash", 0.1), shot("usable-a", 6), shot("usable-b", 6)),
        minimum_chapter_coverage=1,
    )

    assert not plan.blocked
    assert "flash" not in {item.shot_id for item in plan.selected}
