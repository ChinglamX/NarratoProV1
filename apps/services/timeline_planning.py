"""E09 J02 application service: grounded visual planning with artifact persistence.

Orchestrates the deterministic domain functions
(:func:`retrieve_candidates`, :func:`select_grounded_clips`,
:func:`analyze_continuity`, :func:`solve_crop_path`,
:func:`choose_source_subtitle_policy`) and commits every intermediate product
as an immutable artifact with exact-version dependency edges. Incomplete
coverage or continuity blockers keep the outcome fail-closed; no selection
policy lives in this boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection

from packages.contracts import ActorRef, ArtifactRef, ArtifactType, Checksum
from packages.contracts.timeline_intent import (
    ClipRetrievalQuery,
    CompositionTarget,
    CropPath,
    NarrativeBeatGraph,
    SourceSubtitleHandlingPlan,
    VisualPlanningReport,
)
from packages.observability import MetricPoint
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact, payload_checksum
from packages.timeline.creative import select_grounded_clips
from packages.timeline.visual_planning import (
    ClipIndexPort,
    analyze_continuity,
    choose_source_subtitle_policy,
    retrieve_candidates,
    solve_crop_path,
)


class TimelinePlanningError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PlanningArtifactIds:
    """Pre-allocated identities make activities replay-deterministic."""

    candidate_set_id: UUID | None = None
    selection_plan_id: UUID | None = None
    continuity_report_id: UUID | None = None
    visual_report_id: UUID | None = None
    crop_path_ids: Mapping[UUID, UUID] = field(default_factory=dict)
    subtitle_plan_ids: Mapping[UUID, UUID] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VisualPlanningOutcome:
    candidate_set_ref: ArtifactRef
    selection_plan_ref: ArtifactRef
    continuity_report_ref: ArtifactRef
    visual_report_ref: ArtifactRef
    crop_path_refs: tuple[ArtifactRef, ...]
    subtitle_plan_refs: tuple[ArtifactRef, ...]
    coverage_gaps: int
    continuity_blockers: int
    incomplete: bool
    metrics: tuple[MetricPoint, ...]


@dataclass(frozen=True, slots=True)
class _CommitContext:
    project_id: UUID
    run_id: UUID
    variant_id: UUID | None
    trace_id: str
    actor: ActorRef
    resource_profile_ref: ArtifactRef


def _exact_ref(artifact_id: UUID, artifact_type: str, payload: Any) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        version=1,
        artifact_type=ArtifactType(artifact_type),
        checksum=Checksum(payload_checksum(payload.model_dump(mode="json"))),
    )


class TimelinePlanningService:
    def __init__(self, artifacts: ArtifactRepository) -> None:
        self._artifacts = artifacts

    def plan_visual(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        run_id: UUID,
        variant_id: UUID | None,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        beat_graph: NarrativeBeatGraph,
        beat_graph_ref: ArtifactRef,
        queries: Sequence[ClipRetrievalQuery],
        index: ClipIndexPort,
        pinned: Mapping[UUID, UUID] | None = None,
        banned: frozenset[UUID] = frozenset(),
        composition_targets: Mapping[UUID, Sequence[CompositionTarget]] | None = None,
        source_text_track_refs: Mapping[UUID, tuple[UUID, ...]] | None = None,
        story_critical_subtitles: frozenset[UUID] = frozenset(),
        crop_safe_candidates: frozenset[UUID] = frozenset(),
        ids: PlanningArtifactIds | None = None,
    ) -> VisualPlanningOutcome:
        ids = ids or PlanningArtifactIds()
        composition_targets = composition_targets or {}
        source_text_track_refs = source_text_track_refs or {}
        candidate_set_id = ids.candidate_set_id or uuid4()
        selection_plan_id = ids.selection_plan_id or uuid4()
        continuity_report_id = ids.continuity_report_id or uuid4()
        visual_report_id = ids.visual_report_id or uuid4()
        common = _CommitContext(
            project_id=project_id,
            run_id=run_id,
            variant_id=variant_id,
            trace_id=trace_id,
            actor=actor,
            resource_profile_ref=resource_profile_ref,
        )

        candidates = retrieve_candidates(queries=queries, index=index)
        candidate_set, selections = select_grounded_clips(
            candidate_set_ref=ArtifactRef(
                artifact_id=candidate_set_id,
                version=1,
                artifact_type=ArtifactType("ClipCandidateSet"),
            ),
            beat_graph=beat_graph,
            candidates=candidates,
            pinned=dict(pinned) if pinned else None,
            banned=banned,
        )
        candidate_set_ref = _exact_ref(candidate_set_id, "ClipCandidateSet", candidate_set)
        selection_plan = selections.model_copy(update={"candidate_set_ref": candidate_set_ref})
        selection_plan_ref = _exact_ref(selection_plan_id, "ClipSelectionPlan", selection_plan)
        continuity_report = analyze_continuity(
            selection_plan_ref=selection_plan_ref,
            selections=selection_plan,
            candidates=candidate_set.candidates,
        )
        continuity_report_ref = _exact_ref(
            continuity_report_id, "ContinuityReport", continuity_report
        )

        crop_paths: list[CropPath] = []
        for selection in selection_plan.selections:
            targets = composition_targets.get(selection.candidate_id)
            if targets:
                crop_paths.append(
                    solve_crop_path(
                        selection_plan_ref=selection_plan_ref,
                        candidate_id=selection.candidate_id,
                        targets=targets,
                        duration=selection.selected_range.duration,
                    )
                )
        subtitle_plans: list[SourceSubtitleHandlingPlan] = []
        for candidate in candidate_set.candidates:
            subtitle_plans.append(
                choose_source_subtitle_policy(
                    candidate_id=candidate.candidate_id,
                    text_track_refs=source_text_track_refs.get(candidate.candidate_id, ()),
                    required_for_story=candidate.candidate_id in story_critical_subtitles,
                    crop_safe=candidate.candidate_id in crop_safe_candidates,
                )
            )

        crop_path_refs = tuple(
            _exact_ref(ids.crop_path_ids.get(path.candidate_id, uuid4()), "CropPath", path)
            for path in crop_paths
        )
        subtitle_plan_refs = tuple(
            _exact_ref(
                ids.subtitle_plan_ids.get(plan.candidate_id, uuid4()),
                "SourceSubtitleHandlingPlan",
                plan,
            )
            for plan in subtitle_plans
        )

        report = VisualPlanningReport(
            candidate_set_ref=candidate_set_ref,
            selection_plan_ref=selection_plan_ref,
            continuity_report_ref=continuity_report_ref,
            crop_path_refs=crop_path_refs,
            subtitle_plan_refs=subtitle_plan_refs,
            blocker_codes=tuple(risk.risk_type for risk in continuity_report.risks if risk.blocker),
            locally_recomputed_beat_ids=(),
        )
        visual_report_ref = _exact_ref(visual_report_id, "VisualPlanningReport", report)

        self._commit(
            connection,
            artifact_id=candidate_set_id,
            artifact_type="ClipCandidateSet",
            payload=candidate_set,
            inputs=(beat_graph_ref,),
            common=common,
        )
        self._commit(
            connection,
            artifact_id=selection_plan_id,
            artifact_type="ClipSelectionPlan",
            payload=selection_plan,
            inputs=(candidate_set_ref,),
            common=common,
        )
        self._commit(
            connection,
            artifact_id=continuity_report_id,
            artifact_type="ContinuityReport",
            payload=continuity_report,
            inputs=(selection_plan_ref,),
            common=common,
        )
        for path, reference in zip(crop_paths, crop_path_refs, strict=True):
            self._commit(
                connection,
                artifact_id=reference.artifact_id,
                artifact_type="CropPath",
                payload=path,
                inputs=(selection_plan_ref,),
                common=common,
            )
        for plan, reference in zip(subtitle_plans, subtitle_plan_refs, strict=True):
            self._commit(
                connection,
                artifact_id=reference.artifact_id,
                artifact_type="SourceSubtitleHandlingPlan",
                payload=plan,
                inputs=(candidate_set_ref,),
                common=common,
            )
        self._commit(
            connection,
            artifact_id=visual_report_id,
            artifact_type="VisualPlanningReport",
            payload=report,
            inputs=(
                candidate_set_ref,
                selection_plan_ref,
                continuity_report_ref,
                *crop_path_refs,
                *subtitle_plan_refs,
            ),
            common=common,
        )

        metrics = [
            MetricPoint(
                name="timeline_visual_planning",
                value=1,
                labels={
                    "stage": "visual-planning",
                    "state": "incomplete" if candidate_set.incomplete else "succeeded",
                },
            )
        ]
        if continuity_report.blocker_count:
            metrics.append(
                MetricPoint(
                    name="timeline_continuity_blockers",
                    value=continuity_report.blocker_count,
                    labels={"stage": "visual-planning", "state": "blocked"},
                )
            )
        return VisualPlanningOutcome(
            candidate_set_ref=candidate_set_ref,
            selection_plan_ref=selection_plan_ref,
            continuity_report_ref=continuity_report_ref,
            visual_report_ref=visual_report_ref,
            crop_path_refs=crop_path_refs,
            subtitle_plan_refs=subtitle_plan_refs,
            coverage_gaps=len(candidate_set.coverage_gaps),
            continuity_blockers=continuity_report.blocker_count,
            incomplete=candidate_set.incomplete,
            metrics=tuple(metrics),
        )

    def _commit(
        self,
        connection: Connection,
        *,
        artifact_id: UUID,
        artifact_type: str,
        payload: Any,
        inputs: tuple[ArtifactRef, ...],
        common: _CommitContext,
    ) -> ArtifactRef:
        return commit_contract_artifact(
            connection,
            self._artifacts,
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            payload=payload,
            project_id=common.project_id,
            run_id=common.run_id,
            variant_id=common.variant_id,
            trace_id=common.trace_id,
            actor=common.actor,
            producer_module="timeline-planning",
            module_version="e09-j02-v1",
            resource_profile_ref=common.resource_profile_ref,
            rights_class="internal-planning",
            inputs=inputs,
        )
