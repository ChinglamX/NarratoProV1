#!/usr/bin/env python3
"""Dependency-light acceptance for the long-form planning slice."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.longform.clip_planning import CandidateShot, plan_chapter_clips  # noqa: E402
from packages.longform.inventory import build_media_inventory  # noqa: E402
from packages.longform.planning import (  # noqa: E402
    Chapter,
    ChapterBlueprint,
    ChapterFunction,
    MarketingArcCandidate,
    build_chapter_blueprint,
    propose_marketing_arcs,
    select_default_arc,
)
from packages.longform.review import NarrationDraft, review_longform_narration  # noqa: E402
from packages.longform.story_index import SeriesStoryIndex, build_series_story_index  # noqa: E402
from scripts.longform_pipeline import _event  # noqa: E402


def main() -> int:
    _accept_inventory()
    index, arcs, blueprint = _accept_story_and_planning()
    _accept_clip_fail_closed(blueprint)
    _accept_narration_review()
    print(
        "longform acceptance: ok "
        f"({index.episode_count} episodes / {len(index.events)} events / {len(arcs)} arcs)"
    )
    return 0


def _accept_inventory() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "普通剧集" / "剧A").mkdir(parents=True)
        (root / "热门剧集" / "剧A").mkdir(parents=True)
        (root / "普通剧集" / "剧A" / "1.mp4").write_bytes(b"episode")
        (root / "热门剧集" / "剧A" / "热门版.mp4").write_bytes(b"popular")
        result = build_media_inventory(root)
        assert len(result.files) == 2  # nosec B101
        assert result.rights_status == "user_declared_internal_use"  # nosec B101


def _accept_story_and_planning() -> tuple[
    SeriesStoryIndex, tuple[MarketingArcCandidate, ...], ChapterBlueprint
]:
    payload = json.loads(
        (ROOT / "evaluation/evidence/longform/shanshen_series_events.json").read_text(
            encoding="utf-8"
        )
    )
    index = build_series_story_index(
        series_id=payload["series_id"],
        events=tuple(_event(item) for item in payload["events"]),
        unresolved=tuple(payload["unresolved"]),
    )
    arcs = propose_marketing_arcs(index)
    recommendation = select_default_arc(index, arcs)
    blueprint = build_chapter_blueprint(
        index=index,
        arc=recommendation.arc,
        target_seconds=240,
    )
    body = tuple(ref for chapter in blueprint.chapters[1:] for ref in chapter.event_refs)
    assert body == (  # nosec B101
        "fall-and-awaken",
        "wolf-threat",
        "drive-wolves",
        "family-debt",
        "valuable-ginseng",
        "shop-lowball",
        "cash-offer",
        "protect-sister",
    )
    assert not blueprint.blocked  # nosec B101
    return index, arcs, blueprint


def _accept_clip_fail_closed(blueprint: ChapterBlueprint) -> None:
    chapter = blueprint.chapters[0]
    isolated = ChapterBlueprint(
        arc_id=blueprint.arc_id,
        target_seconds=chapter.target_seconds,
        chapters=(
            Chapter(
                chapter_id=chapter.chapter_id,
                function=ChapterFunction.HOOK,
                event_refs=chapter.event_refs,
                target_seconds=chapter.target_seconds,
                narration_budget_seconds=chapter.narration_budget_seconds,
                protects_original_audio=chapter.protects_original_audio,
            ),
        ),
        findings=(),
    )
    insufficient = (
        CandidateShot(
            shot_id="one-short-shot",
            source_path="episode-1.mp4",
            episode=1,
            start_seconds=0,
            duration_seconds=1,
            event_refs=chapter.event_refs,
            visual_score=1,
            contains_protected_audio=chapter.protects_original_audio,
        ),
    )
    plan = plan_chapter_clips(blueprint=isolated, shots=insufficient)
    assert plan.blocked  # nosec B101
    assert plan.findings[0].code == "insufficient-unique-media-coverage"  # nosec B101


def _accept_narration_review() -> None:
    accepted = NarrationDraft(
        line_id="line-1",
        chapter_id="chapter-1",
        text="狼群退去后，真正压在兄妹身上的债务才刚刚出现。",  # noqa: RUF001
        event_refs=("family-debt",),
        visual_event_refs=("wolves-retreat",),
        dialogue_excerpts=("狼都退了",),
        measured_duration_seconds=4,
        available_seconds=8,
    )
    assert not review_longform_narration((accepted,)).blocked  # nosec B101
    overflow = NarrationDraft(
        line_id="line-2",
        chapter_id="chapter-1",
        text="真正的危机才刚刚开始。",
        event_refs=("family-debt",),
        visual_event_refs=(),
        dialogue_excerpts=(),
        measured_duration_seconds=9,
        available_seconds=4,
    )
    assert review_longform_narration((overflow,)).blocked  # nosec B101


if __name__ == "__main__":
    raise SystemExit(main())
