"""Project long-form decisions into the existing E09 canonical timeline contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from packages.contracts import ArtifactRef, RationalTime, TimeRange
from packages.contracts.timeline_intent import (
    BeatFunction,
    ClipCandidate,
    ClipCandidateSet,
    ClipSelection,
    ClipSelectionPlan,
    ContinuityRisk,
    NarrativeBeat,
    NarrativeBeatGraph,
)
from packages.longform.clip_planning import ChapterClipPlan, SelectedShot
from packages.longform.planning import ChapterBlueprint, ChapterFunction


@dataclass(frozen=True)
class CanonicalTimelineInputs:
    beat_graph: NarrativeBeatGraph
    candidate_set: ClipCandidateSet
    selection_plan: ClipSelectionPlan


def project_to_canonical_timeline_inputs(
    *,
    blueprint: ChapterBlueprint,
    clip_plan: ChapterClipPlan,
    creative_brief_ref: ArtifactRef,
    candidate_set_ref: ArtifactRef,
    source_refs: Mapping[str, ArtifactRef],
    story_refs: Mapping[str, UUID],
    evidence_refs: Mapping[str, tuple[UUID, ...]],
) -> CanonicalTimelineInputs:
    """Create canonical inputs only for a complete, fully grounded video plan.

    The adapter deliberately accepts refs from upstream artifact persistence. It
    never manufactures Story, Evidence or SourceMedia identities locally.
    """

    if blueprint.blocked or clip_plan.blocked:
        raise ValueError("blocked long-form plans cannot enter the canonical timeline")
    if creative_brief_ref.artifact_type != "CreativeBrief":
        raise ValueError("creative_brief_ref must reference CreativeBrief")
    if candidate_set_ref.artifact_type != "ClipCandidateSet":
        raise ValueError("candidate_set_ref must reference ClipCandidateSet")

    selected_by_chapter: dict[str, list[SelectedShot]] = {
        chapter.chapter_id: [] for chapter in blueprint.chapters
    }
    for shot in clip_plan.selected:
        if shot.chapter_id not in selected_by_chapter:
            raise ValueError(f"selected shot references unknown chapter: {shot.chapter_id}")
        selected_by_chapter[shot.chapter_id].append(shot)

    beats: list[NarrativeBeat] = []
    candidates: list[ClipCandidate] = []
    selections: list[ClipSelection] = []
    continuity_risks: list[ContinuityRisk] = []
    previous: tuple[UUID, SelectedShot] | None = None

    for chapter in blueprint.chapters:
        shots = selected_by_chapter[chapter.chapter_id]
        selected_seconds = sum(shot.duration_seconds for shot in shots)
        if abs(selected_seconds - chapter.target_seconds) > 0.002:
            raise ValueError(
                f"chapter {chapter.chapter_id} has {selected_seconds:.3f}s but requires "
                f"{chapter.target_seconds:.3f}s of unique video"
            )
        for position, shot in enumerate(shots, 1):
            source_ref = source_refs.get(shot.source_path)
            if source_ref is None or source_ref.artifact_type != "SourceMedia":
                raise ValueError(f"missing SourceMedia ref for {shot.source_path}")
            missing_story = tuple(ref for ref in shot.event_refs if ref not in story_refs)
            shot_evidence = evidence_refs.get(shot.shot_id, ())
            if missing_story or not shot_evidence:
                raise ValueError(f"shot {shot.shot_id} lacks persisted Story/Evidence refs")

            beat_id = _uuid(f"longform-beat:{blueprint.arc_id}:{chapter.chapter_id}:{position}")
            candidate_id = _uuid(f"longform-candidate:{shot.shot_id}:{chapter.chapter_id}")
            duration = _time(shot.duration_seconds)
            canonical_story_refs = tuple(story_refs[ref] for ref in shot.event_refs)
            beats.append(
                NarrativeBeat(
                    beat_id=beat_id,
                    function=_beat_function(chapter.function),
                    story_refs=canonical_story_refs,
                    target_duration=duration,
                    minimum_duration=duration,
                    maximum_duration=duration,
                    required_information=tuple(f"event:{ref}" for ref in shot.event_refs),
                    emotional_intent={"chapter_function": chapter.function.value},
                    locked=chapter.protects_original_audio and shot.contains_protected_audio,
                )
            )
            candidates.append(
                ClipCandidate(
                    candidate_id=candidate_id,
                    beat_id=beat_id,
                    source_ref=source_ref,
                    source_range=TimeRange(start=_time(shot.start_seconds), duration=duration),
                    story_refs=canonical_story_refs,
                    evidence_refs=shot_evidence,
                    quality={"longform_selected": True},
                    continuity_features={"episode": shot.episode},
                    reframe_feasible=True,
                    rights_allowed=True,
                    score_components={"evidence_grounding": 1.0},
                )
            )
            selections.append(
                ClipSelection(
                    beat_id=beat_id,
                    candidate_id=candidate_id,
                    selected_range=TimeRange(start=_time(shot.start_seconds), duration=duration),
                    rationale="approved chapter plan; unique evidence-grounded shot",
                )
            )
            if previous is not None and previous[1].episode != shot.episode:
                continuity_risks.append(
                    ContinuityRisk(
                        left_candidate_id=previous[0],
                        right_candidate_id=candidate_id,
                        risk_type="cross-episode-transition",
                        severity=1,
                        explanation="episode boundary requires visual continuity review",
                    )
                )
            previous = (candidate_id, shot)

    graph = NarrativeBeatGraph(
        creative_brief_ref=creative_brief_ref,
        beats=tuple(beats),
        target_duration=_time(blueprint.target_seconds),
    )
    candidate_set = ClipCandidateSet(
        beat_graph_ref=creative_brief_ref,
        candidates=tuple(candidates),
    )
    selection_plan = ClipSelectionPlan(
        candidate_set_ref=candidate_set_ref,
        selections=tuple(selections),
        continuity_risks=tuple(continuity_risks),
    )
    return CanonicalTimelineInputs(graph, candidate_set, selection_plan)


def _uuid(key: str) -> UUID:
    raw = bytearray(sha256(key.encode()).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))


def _time(seconds: float) -> RationalTime:
    return RationalTime(value=round(seconds * 1_000_000), rate_num=1_000_000)


def _beat_function(function: ChapterFunction) -> BeatFunction:
    return {
        ChapterFunction.HOOK: BeatFunction.HOOK,
        ChapterFunction.SETUP: BeatFunction.CONTEXT,
        ChapterFunction.CONFLICT: BeatFunction.ESCALATION,
        ChapterFunction.ESCALATION: BeatFunction.ESCALATION,
        ChapterFunction.TURN: BeatFunction.TURN,
        ChapterFunction.CLIMAX: BeatFunction.PAYOFF,
        ChapterFunction.PAYOFF: BeatFunction.PAYOFF,
        ChapterFunction.CONTINUATION: BeatFunction.CTA,
    }[function]
