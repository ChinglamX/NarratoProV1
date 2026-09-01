"""Evidence and budget preflight for long-form narration drafts before TTS."""

from __future__ import annotations

from dataclasses import dataclass

from packages.intelligence.narration_draft import validate_narration_draft
from packages.longform.planning import ChapterBlueprint
from packages.longform.story_index import SeriesStoryIndex


@dataclass(frozen=True)
class NarrationTextDraft:
    line_id: str
    chapter_id: str
    text: str
    event_refs: tuple[str, ...]
    rhetorical: bool = False


@dataclass(frozen=True)
class NarrationPreflightFinding:
    line_id: str
    code: str
    blocker: bool
    explanation: str


@dataclass(frozen=True)
class NarrationPreflight:
    estimated_duration_seconds: float
    chapter_estimates: tuple[tuple[str, float], ...]
    findings: tuple[NarrationPreflightFinding, ...]

    @property
    def blocked(self) -> bool:
        return any(finding.blocker for finding in self.findings)


def preflight_narration_drafts(
    *,
    drafts: tuple[NarrationTextDraft, ...],
    story_index: SeriesStoryIndex,
    blueprint: ChapterBlueprint,
    estimated_characters_per_second: float = 4.2,
) -> NarrationPreflight:
    """Reject ungrounded/duplicate text and estimate chapter load before paid TTS."""

    if estimated_characters_per_second <= 0:
        raise ValueError("estimated speech rate must be positive")
    events = {event.event_id: event for event in story_index.events}
    chapters = {chapter.chapter_id: chapter for chapter in blueprint.chapters}
    chapter_seconds = {chapter.chapter_id: 0.0 for chapter in blueprint.chapters}
    findings: list[NarrationPreflightFinding] = []
    seen: set[str] = set()

    for draft in drafts:
        if draft.chapter_id not in chapters:
            findings.append(_finding(draft, "unknown-chapter", True, draft.chapter_id))
            continue
        missing = tuple(ref for ref in draft.event_refs if ref not in events)
        if not draft.event_refs or missing:
            explanation = "no event refs" if not draft.event_refs else f"unknown refs: {missing}"
            findings.append(_finding(draft, "missing-story-evidence", True, explanation))
            continue
        chapter_refs = set(chapters[draft.chapter_id].event_refs)
        if not chapter_refs.intersection(draft.event_refs):
            findings.append(
                _finding(draft, "chapter-event-mismatch", True, "line has no event in its chapter")
            )
        excerpts = tuple(
            evidence.excerpt
            for ref in draft.event_refs
            for evidence in events[ref].evidence
            if evidence.kind == "dialogue" and evidence.excerpt
        )
        for violation in validate_narration_draft(draft.text, dialogue_excerpts=excerpts):
            findings.append(_finding(draft, violation, True, "narration rule failed"))
        normalized = _normalize(draft.text)
        if normalized in seen:
            findings.append(_finding(draft, "duplicate-narration", True, "duplicate text"))
        seen.add(normalized)
        duration = len(normalized) / estimated_characters_per_second
        chapter_seconds[draft.chapter_id] += duration

    for chapter_id, duration in chapter_seconds.items():
        budget = chapters[chapter_id].narration_budget_seconds
        if duration > budget:
            findings.append(
                NarrationPreflightFinding(
                    line_id="*",
                    code="estimated-chapter-budget-overflow",
                    blocker=True,
                    explanation=f"{chapter_id}: {duration:.3f}s > {budget:.3f}s",
                )
            )
    estimates = tuple((chapter_id, seconds) for chapter_id, seconds in chapter_seconds.items())
    return NarrationPreflight(
        estimated_duration_seconds=sum(chapter_seconds.values()),
        chapter_estimates=estimates,
        findings=tuple(findings),
    )


def _finding(
    draft: NarrationTextDraft, code: str, blocker: bool, explanation: str
) -> NarrationPreflightFinding:
    return NarrationPreflightFinding(
        line_id=draft.line_id,
        code=code,
        blocker=blocker,
        explanation=explanation,
    )


def _normalize(value: str) -> str:
    return "".join(character for character in value if character.isalnum()).lower()
