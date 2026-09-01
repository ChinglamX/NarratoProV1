"""E09 J03 application service: rhythm budgets and evidence-constrained narration.

Orchestrates :func:`allocate_rhythm`, :func:`review_narration` and
:func:`replace_lines_in_scope`, committing every product as an immutable
artifact with exact-version dependency edges. An infeasible duration budget is
reported as an explicit ``DurationConflict`` and commits nothing; narration
text is never generated here (L1 human-approved line sets only).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import Connection

from packages.contracts import ActorRef, ArtifactRef
from packages.contracts.timeline_intent import (
    DurationConflict,
    NarrationLine,
    NarrationLineSet,
    NarrativeBeatGraph,
)
from packages.observability import MetricPoint
from packages.persistence.artifact_repository import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.timeline.narration import NarrationSourcePort
from packages.timeline.rhythm_narration import (
    allocate_rhythm,
    replace_lines_in_scope,
    review_narration,
)


class RhythmPlanningError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RhythmPlanningOutcome:
    rhythm_plan_ref: ArtifactRef | None
    duration_conflict: DurationConflict | None
    narration_report_ref: ArtifactRef | None
    updated_line_set_ref: ArtifactRef | None
    metrics: tuple[MetricPoint, ...]


class RhythmPlanningService:
    def __init__(self, artifacts: ArtifactRepository) -> None:
        self._artifacts = artifacts

    def plan_rhythm(
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
        selection_plan_ref: ArtifactRef,
        rhythm_plan_id: UUID | None = None,
    ) -> RhythmPlanningOutcome:
        plan, conflict = allocate_rhythm(
            beat_graph_ref=beat_graph_ref,
            selection_plan_ref=selection_plan_ref,
            graph=beat_graph,
        )
        if conflict is not None:
            return RhythmPlanningOutcome(
                rhythm_plan_ref=None,
                duration_conflict=conflict,
                narration_report_ref=None,
                updated_line_set_ref=None,
                metrics=(
                    MetricPoint(
                        name="timeline_rhythm_conflict",
                        value=1,
                        labels={"stage": "rhythm-planning", "state": "blocked"},
                    ),
                ),
            )
        if plan is None:
            raise RhythmPlanningError("rhythm allocation produced neither plan nor conflict")
        rhythm_plan_id = rhythm_plan_id or uuid4()
        rhythm_plan_ref = commit_contract_artifact(
            connection,
            self._artifacts,
            artifact_id=rhythm_plan_id,
            artifact_type="RhythmPlan",
            payload=plan,
            project_id=project_id,
            run_id=run_id,
            variant_id=variant_id,
            trace_id=trace_id,
            actor=actor,
            producer_module="rhythm-planning",
            module_version="e09-j03-v1",
            resource_profile_ref=resource_profile_ref,
            rights_class="internal-planning",
            inputs=(beat_graph_ref, selection_plan_ref),
        )
        return RhythmPlanningOutcome(
            rhythm_plan_ref=rhythm_plan_ref,
            duration_conflict=None,
            narration_report_ref=None,
            updated_line_set_ref=None,
            metrics=(
                MetricPoint(
                    name="timeline_rhythm_planning",
                    value=1,
                    labels={"stage": "rhythm-planning", "state": "succeeded"},
                ),
            ),
        )

    def review_lines(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        run_id: UUID,
        variant_id: UUID | None,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        line_set: NarrationLineSet,
        line_set_ref: ArtifactRef,
        dialogue_by_beat: Mapping[UUID, Sequence[str]],
        report_id: UUID | None = None,
    ) -> ArtifactRef:
        report = review_narration(
            line_set_ref=line_set_ref, lines=line_set, dialogue_by_beat=dialogue_by_beat
        )
        report_id = report_id or uuid4()
        return commit_contract_artifact(
            connection,
            self._artifacts,
            artifact_id=report_id,
            artifact_type="NarrationPlanningReport",
            payload=report,
            project_id=project_id,
            run_id=run_id,
            variant_id=variant_id,
            trace_id=trace_id,
            actor=actor,
            producer_module="rhythm-planning",
            module_version="e09-j03-v1",
            resource_profile_ref=resource_profile_ref,
            rights_class="internal-planning",
            inputs=(line_set_ref,),
        )

    def replace_lines(
        self,
        connection: Connection,
        *,
        project_id: UUID,
        run_id: UUID,
        variant_id: UUID | None,
        trace_id: str,
        actor: ActorRef,
        resource_profile_ref: ArtifactRef,
        source: NarrationSourcePort,
        current_ref: ArtifactRef,
        replacements: Mapping[UUID, NarrationLine],
        new_line_set_id: UUID | None = None,
    ) -> tuple[ArtifactRef, NarrationLineSet]:
        current = source.load(current_ref)
        updated = replace_lines_in_scope(current, replacements)
        new_line_set_id = new_line_set_id or uuid4()
        updated_ref = commit_contract_artifact(
            connection,
            self._artifacts,
            artifact_id=new_line_set_id,
            artifact_type="NarrationLineSet",
            payload=updated,
            project_id=project_id,
            run_id=run_id,
            variant_id=variant_id,
            trace_id=trace_id,
            actor=actor,
            producer_module="rhythm-planning",
            module_version="e09-j03-v1",
            resource_profile_ref=resource_profile_ref,
            rights_class="internal-planning",
            inputs=(current_ref,),
        )
        return updated_ref, updated
