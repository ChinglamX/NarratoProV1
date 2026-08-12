"""Deterministic rhythm budgets and evidence-constrained narration checks."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from packages.contracts import ArtifactRef, RationalTime
from packages.contracts.timeline_intent import (
    BeatRhythm,
    DurationConflict,
    NarrationFinding,
    NarrationLine,
    NarrationLineSet,
    NarrationPlanningReport,
    NarrativeBeatGraph,
    RhythmPlan,
)


def allocate_rhythm(
    *, beat_graph_ref: ArtifactRef, selection_plan_ref: ArtifactRef, graph: NarrativeBeatGraph
) -> tuple[RhythmPlan | None, DurationConflict | None]:
    minimum = sum(beat.minimum_duration.seconds for beat in graph.beats)
    available = graph.target_duration.seconds
    if minimum > available:
        return None, DurationConflict(
            minimum_required=RationalTime(value=int(minimum), rate_num=1),
            available=graph.target_duration,
            affected_beat_ids=tuple(beat.beat_id for beat in graph.beats),
            alternatives=("remove-non-core-beat", "change-expression", "return-to-gate-2"),
        )
    targets = [beat.target_duration.seconds for beat in graph.beats]
    scale = available / sum(targets)
    values = [round(value * scale) for value in targets]
    values[-1] += int(available - sum(values))
    beats = tuple(
        BeatRhythm(
            beat_id=beat.beat_id,
            target_duration=RationalTime(value=value, rate_num=1),
            entry_energy=_number(beat.emotional_intent.get("entry_energy"), 0.4),
            exit_energy=_number(beat.emotional_intent.get("exit_energy"), 0.6),
            information_density=_number(beat.emotional_intent.get("information_density"), 0.6),
            breathing_point=beat.function.value in {"context", "payoff"},
        )
        for beat, value in zip(graph.beats, values, strict=True)
    )
    return RhythmPlan(
        beat_graph_ref=beat_graph_ref,
        selection_plan_ref=selection_plan_ref,
        beats=beats,
        target_duration=graph.target_duration,
    ), None


def review_narration(
    *,
    line_set_ref: ArtifactRef,
    lines: NarrationLineSet,
    dialogue_by_beat: Mapping[object, Sequence[str]],
) -> NarrationPlanningReport:
    findings: list[NarrationFinding] = []
    grounded = 0
    for line in lines.lines:
        if line.story_refs and line.evidence_refs:
            grounded += 1
        normalized = _normalize(line.text)
        if any(normalized == _normalize(text) for text in dialogue_by_beat.get(line.beat_id, ())):
            findings.append(
                NarrationFinding(
                    line_id=line.line_id,
                    code="dialogue-repetition",
                    explanation="line repeats source dialogue",
                    blocker=True,
                )
            )
        if (
            any(token in line.text for token in ("他心里想", "她心里想", "注定"))
            and not line.rhetorical
        ):
            findings.append(
                NarrationFinding(
                    line_id=line.line_id,
                    code="unsupported-psychology",
                    explanation="psychology requires approved Story evidence",
                    blocker=True,
                )
            )
    total = len(lines.lines)
    return NarrationPlanningReport(
        line_set_ref=line_set_ref,
        findings=tuple(findings),
        evidence_coverage=grounded / total if total else 0.0,
        estimated_seconds=float(lines.estimated_duration.seconds),
        locked_line_ids=tuple(line.line_id for line in lines.lines if line.locked),
    )


def replace_lines_in_scope(
    current: NarrationLineSet, replacements: Mapping[object, NarrationLine]
) -> NarrationLineSet:
    lines = []
    for line in current.lines:
        replacement = replacements.get(line.line_id)
        if replacement is not None and line.locked:
            raise ValueError("locked narration line cannot be regenerated")
        lines.append(replacement or line)
    return current.model_copy(update={"lines": tuple(lines)})


def _normalize(value: str) -> str:
    return "".join(character for character in value if character.isalnum()).lower()


def _number(value: object, default: float) -> float:
    return float(value) if isinstance(value, int | float) else default
