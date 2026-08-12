"""Deterministic bounded candidate assembly around model- or human-proposed content."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from uuid import UUID, uuid4

from packages.contracts import (
    ArtifactRef,
    ConfidenceRecord,
    HookCandidate,
    NarrativeRole,
    RiskClass,
    SellingPoint,
    SellingPointSet,
    StoryGraph,
)
from packages.contracts.strategy_candidates import (
    CandidateBlocker,
    CandidateBudget,
    CandidateDisposition,
    CandidateValidation,
    HookCandidateSet,
    SellingPointCoverage,
)


def discover_selling_points(
    *,
    approved_story_ref: ArtifactRef,
    story: StoryGraph,
    taxonomy_version: str,
    taxonomy_by_event_importance: Mapping[str, str],
    budget: CandidateBudget,
    confidence: ConfidenceRecord,
    id_factory: Callable[[], UUID] = uuid4,
) -> tuple[SellingPointSet, SellingPointCoverage]:
    """Build evidence-backed candidates from configured Event taxonomy; never invent events."""

    points: list[SellingPoint] = []
    seen: set[tuple[str, tuple[UUID, ...], str]] = set()
    for event in sorted(story.events, key=lambda item: item.order_key):
        taxonomy = taxonomy_by_event_importance.get(event.importance.value, "unknown")
        signature = (taxonomy, (event.event_id,), "core")
        if signature in seen:
            continue
        seen.add(signature)
        points.append(
            SellingPoint(
                selling_point_id=id_factory(),
                taxonomy_type=taxonomy,
                description=event.description,
                story_refs=(event.event_id,),
                evidence=event.evidence,
                narrative_role=NarrativeRole.CORE,
                audience_rationale="Candidate requires human audience validation",
                platform_fit=(),
                spoiler_level=0,
                source_coverage={"event_count": 1},
                risk_class=(
                    RiskClass.HIGH
                    if event.confidence.status.value != "calibrated"
                    else RiskClass.MEDIUM
                ),
                heuristic_components={"evidence_coverage": 1.0},
                confidence=confidence,
                assumptions=("Marketing relevance is uncalibrated",),
            )
        )
        if len(points) >= budget.max_selling_points:
            break
    all_ids = tuple(item.event_id for item in story.events)
    covered = tuple(ref for point in points for ref in point.story_refs)
    coverage = SellingPointCoverage(
        story_ref_ids=all_ids,
        covered_story_ref_ids=tuple(dict.fromkeys(covered)),
        uncovered_story_ref_ids=tuple(item for item in all_ids if item not in covered),
    )
    return (
        SellingPointSet(
            approved_story_ref=approved_story_ref,
            taxonomy_version=taxonomy_version,
            selling_points=tuple(points),
            incomplete=len(points) < min(len(story.events), budget.max_selling_points),
        ),
        coverage,
    )


def validate_hook(
    hook: HookCandidate,
    *,
    approved_story_ref: ArtifactRef,
    known_story_refs: set[UUID],
    allowed_mechanics: set[str],
) -> CandidateValidation:
    blockers: list[CandidateBlocker] = []
    if hook.hook_type not in allowed_mechanics:
        blockers.append(
            CandidateBlocker(
                code="unsupported-hook-mechanic",
                field="hook_type",
                detail="Hook mechanic is not enabled by the effective profile",
                story_ref=approved_story_ref,
            )
        )
    if not set(hook.source_moment_refs) <= known_story_refs:
        blockers.append(
            CandidateBlocker(
                code="unknown-source-moment",
                field="source_moment_refs",
                detail="Hook references a moment outside the approved Story",
                story_ref=approved_story_ref,
            )
        )
    if not set(hook.continuation_beats) <= known_story_refs:
        blockers.append(
            CandidateBlocker(
                code="broken-continuation",
                field="continuation_beats",
                detail="Hook continuation does not resolve inside approved Story",
                story_ref=approved_story_ref,
            )
        )
    return CandidateValidation(
        candidate_id=hook.hook_id,
        disposition=(CandidateDisposition.REJECTED if blockers else CandidateDisposition.VALID),
        blockers=tuple(blockers),
    )


def assemble_hook_set(
    *,
    approved_story_ref: ArtifactRef,
    strategy_candidate_set_ref: ArtifactRef,
    proposed: Sequence[HookCandidate],
    known_story_refs: set[UUID],
    allowed_mechanics: set[str],
    budget: CandidateBudget,
) -> HookCandidateSet:
    scheduled = tuple(proposed[: budget.max_total_candidates])
    validations = tuple(
        validate_hook(
            item,
            approved_story_ref=approved_story_ref,
            known_story_refs=known_story_refs,
            allowed_mechanics=allowed_mechanics,
        )
        for item in scheduled
    )
    return HookCandidateSet(
        approved_story_ref=approved_story_ref,
        strategy_candidate_set_ref=strategy_candidate_set_ref,
        candidates=scheduled,
        validations=validations,
        incomplete=len(proposed) > len(scheduled),
    )
