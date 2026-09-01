"""Deterministic long-form narration and chapter quality checks."""

from __future__ import annotations

from dataclasses import dataclass

from packages.intelligence.narration_draft import validate_narration_draft


@dataclass(frozen=True)
class NarrationDraft:
    line_id: str
    chapter_id: str
    text: str
    event_refs: tuple[str, ...]
    visual_event_refs: tuple[str, ...]
    dialogue_excerpts: tuple[str, ...]
    measured_duration_seconds: float
    available_seconds: float


@dataclass(frozen=True)
class LongformNarrationFinding:
    line_id: str
    code: str
    blocker: bool
    explanation: str


@dataclass(frozen=True)
class LongformNarrationReview:
    findings: tuple[LongformNarrationFinding, ...]
    evidence_coverage: float
    visual_alignment_coverage: float
    narration_occupancy: float

    @property
    def blocked(self) -> bool:
        return any(item.blocker for item in self.findings)


def review_longform_narration(lines: tuple[NarrationDraft, ...]) -> LongformNarrationReview:
    findings: list[LongformNarrationFinding] = []
    grounded = 0
    visually_grounded = 0
    normalized_seen: set[str] = set()
    total_duration = 0.0
    total_available = 0.0
    for line in lines:
        if line.measured_duration_seconds <= 0 or line.available_seconds <= 0:
            findings.append(_finding(line, "invalid-duration", True, "timing must be positive"))
            continue
        total_duration += line.measured_duration_seconds
        total_available += line.available_seconds
        if line.event_refs:
            grounded += 1
        else:
            findings.append(
                _finding(line, "missing-story-evidence", True, "line has no story event reference")
            )
        if line.visual_event_refs:
            visually_grounded += 1
        else:
            findings.append(
                _finding(
                    line, "missing-visual-evidence", True, "line has no visual event reference"
                )
            )
        for violation in validate_narration_draft(
            line.text,
            dialogue_excerpts=line.dialogue_excerpts,
        ):
            findings.append(_finding(line, violation, True, "existing narration rule failed"))
        overlap = max(
            (_character_overlap(line.text, excerpt) for excerpt in line.dialogue_excerpts),
            default=0.0,
        )
        if overlap > 0.3:
            findings.append(
                _finding(
                    line,
                    "dialogue-overlap-high",
                    True,
                    f"normalized character overlap is {overlap:.3f}",
                )
            )
        if line.measured_duration_seconds > line.available_seconds:
            findings.append(
                _finding(line, "tts-duration-overflow", True, "voice does not fit its beat")
            )
        normalized = _normalize(line.text)
        if normalized in normalized_seen:
            findings.append(
                _finding(line, "duplicate-narration", True, "same narration appears more than once")
            )
        normalized_seen.add(normalized)

    count = len(lines)
    occupancy = total_duration / total_available if total_available else 0.0
    if occupancy > 0.72 and lines:
        findings.append(
            LongformNarrationFinding(
                line_id="*",
                code="narration-density-fatigue",
                blocker=False,
                explanation=f"overall narration occupancy {occupancy:.3f} exceeds 0.72",
            )
        )
    return LongformNarrationReview(
        findings=tuple(findings),
        evidence_coverage=grounded / count if count else 0.0,
        visual_alignment_coverage=visually_grounded / count if count else 0.0,
        narration_occupancy=occupancy,
    )


def _finding(
    line: NarrationDraft, code: str, blocker: bool, explanation: str
) -> LongformNarrationFinding:
    return LongformNarrationFinding(
        line_id=line.line_id,
        code=code,
        blocker=blocker,
        explanation=explanation,
    )


def _character_overlap(text: str, excerpt: str) -> float:
    left = set(_normalize(text))
    right = set(_normalize(excerpt))
    return len(left & right) / len(left) if left else 0.0


def _normalize(value: str) -> str:
    return "".join(character for character in value if character.isalnum()).lower()
