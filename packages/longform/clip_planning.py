"""Chapter-aware selection over existing shot candidates."""

from __future__ import annotations

from dataclasses import dataclass, replace

from packages.longform.planning import ChapterBlueprint


@dataclass(frozen=True)
class CandidateShot:
    shot_id: str
    source_path: str
    episode: int
    start_seconds: float
    duration_seconds: float
    event_refs: tuple[str, ...]
    visual_score: float
    continuity_group: str | None = None
    contains_protected_audio: bool = False

    def __post_init__(self) -> None:
        if not self.shot_id or not self.source_path or not self.event_refs:
            raise ValueError("shot identity, source and event evidence are required")
        if self.episode < 1 or self.start_seconds < 0 or self.duration_seconds <= 0:
            raise ValueError("shot source range must be valid")
        if not 0 <= self.visual_score <= 1:
            raise ValueError("visual score must be between 0 and 1")


@dataclass(frozen=True)
class SelectedShot:
    chapter_id: str
    shot_id: str
    source_path: str
    episode: int
    start_seconds: float
    duration_seconds: float
    event_refs: tuple[str, ...]
    contains_protected_audio: bool


@dataclass(frozen=True)
class ClipPlanningFinding:
    chapter_id: str
    code: str
    blocker: bool
    explanation: str


@dataclass(frozen=True)
class ChapterClipPlan:
    target_seconds: float
    selected: tuple[SelectedShot, ...]
    findings: tuple[ClipPlanningFinding, ...]

    @property
    def blocked(self) -> bool:
        return any(item.blocker for item in self.findings)

    @property
    def selected_seconds(self) -> float:
        return sum(item.duration_seconds for item in self.selected)


def plan_chapter_clips(
    *,
    blueprint: ChapterBlueprint,
    shots: tuple[CandidateShot, ...],
    minimum_chapter_coverage: float = 0.8,
    minimum_shot_seconds: float = 0.5,
    maximum_shot_seconds: float = 8.0,
) -> ChapterClipPlan:
    """Select unique evidence shots and fail when long-form coverage is insufficient."""

    if not 0 < minimum_chapter_coverage <= 1:
        raise ValueError("minimum chapter coverage must be in (0, 1]")
    if minimum_shot_seconds <= 0 or maximum_shot_seconds < minimum_shot_seconds:
        raise ValueError("shot duration bounds must be positive and ordered")
    used: set[str] = set()
    selected: list[SelectedShot] = []
    findings: list[ClipPlanningFinding] = []
    previous_group: str | None = None

    for chapter_index, chapter in enumerate(blueprint.chapters):
        chapter_selection_start = len(selected)
        wanted = set(chapter.event_refs)
        candidates = [
            shot
            for shot in shots
            if shot.shot_id not in used and wanted.intersection(shot.event_refs)
        ]
        candidates.sort(
            key=lambda shot: (
                1 if previous_group and shot.continuity_group == previous_group else 0,
                1 if chapter.protects_original_audio and shot.contains_protected_audio else 0,
                shot.visual_score,
                -shot.episode,
                -shot.start_seconds,
            ),
            reverse=True,
        )
        chapter_seconds = 0.0
        future_refs = {
            ref for future in blueprint.chapters[chapter_index + 1 :] for ref in future.event_refs
        }
        reserve_for_future = bool(wanted & future_refs) and len(candidates) > 1
        selection_limit = len(candidates) - 1 if reserve_for_future else len(candidates)
        selected_count = 0
        for shot in candidates:
            if chapter_seconds >= chapter.target_seconds or selected_count >= selection_limit:
                break
            if shot.duration_seconds < minimum_shot_seconds:
                continue
            remaining = chapter.target_seconds - chapter_seconds
            duration = min(shot.duration_seconds, maximum_shot_seconds)
            if remaining >= minimum_shot_seconds:
                duration = min(duration, remaining)
            else:
                # A sub-threshold flash is worse than a bounded chapter overrun.
                # Keep a reviewable minimum clip and let the timeline report the
                # small budget variance instead of emitting 1-4 frame fragments.
                duration = min(duration, minimum_shot_seconds)
            if duration <= 0:
                continue
            selected.append(
                SelectedShot(
                    chapter_id=chapter.chapter_id,
                    shot_id=shot.shot_id,
                    source_path=shot.source_path,
                    episode=shot.episode,
                    start_seconds=shot.start_seconds,
                    duration_seconds=duration,
                    event_refs=shot.event_refs,
                    contains_protected_audio=shot.contains_protected_audio,
                )
            )
            used.add(shot.shot_id)
            selected_count += 1
            chapter_seconds += duration
            previous_group = shot.continuity_group

        # Ranking decides which shots earn a place; it must not become edit order.
        # Restore the chapter's causal event order and then the source chronology so
        # a high visual score cannot place a consequence before its setup.
        event_order = {event_ref: index for index, event_ref in enumerate(chapter.event_refs)}
        chapter_selection = selected[chapter_selection_start:]
        overrun = sum(item.duration_seconds for item in chapter_selection) - chapter.target_seconds
        if overrun > 0:
            trim_index = max(
                range(len(chapter_selection)),
                key=lambda index: chapter_selection[index].duration_seconds,
            )
            trim_item = chapter_selection[trim_index]
            if trim_item.duration_seconds - overrun < minimum_shot_seconds:
                raise ValueError("chapter budget cannot be normalized without a flash frame")
            chapter_selection[trim_index] = replace(
                trim_item,
                duration_seconds=trim_item.duration_seconds - overrun,
            )
        chapter_selection.sort(
            key=lambda item: (
                min(event_order[ref] for ref in item.event_refs if ref in event_order),
                item.episode,
                item.start_seconds,
                item.shot_id,
            )
        )
        selected[chapter_selection_start:] = chapter_selection

        required = chapter.target_seconds * minimum_chapter_coverage
        if chapter_seconds < required:
            findings.append(
                ClipPlanningFinding(
                    chapter_id=chapter.chapter_id,
                    code="insufficient-unique-media-coverage",
                    blocker=True,
                    explanation=(
                        f"selected {chapter_seconds:.3f}s; requires at least {required:.3f}s "
                        "without duplicate shots"
                    ),
                )
            )
        if chapter.protects_original_audio and not any(
            item.chapter_id == chapter.chapter_id and item.contains_protected_audio
            for item in selected
        ):
            findings.append(
                ClipPlanningFinding(
                    chapter_id=chapter.chapter_id,
                    code="missing-protected-original-audio-shot",
                    blocker=True,
                    explanation="chapter requires an original-audio beat but none was selected",
                )
            )

    return ChapterClipPlan(
        target_seconds=blueprint.target_seconds,
        selected=tuple(selected),
        findings=tuple(findings),
    )
