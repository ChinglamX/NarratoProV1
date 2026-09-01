"""Durable E09 candidate-to-demo workflow with fail-closed stage gating.

Runs the real planning/assembly/preview chain as separate activities and
finishes with a mandatory human Timeline checkpoint; blocked stages never
auto-repair, and a revise decision returns revision_required instead of
silently continuing.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.project.models import ReviewSignal
    from workflows.timeline.creative_activities import (
        assemble_timeline_activity,
        plan_rhythm_activity,
        plan_visual_activity,
        render_media_preview_activity,
        review_narration_activity,
    )
    from workflows.timeline.creative_models import (
        AssemblyActivityRequest,
        CreativeTimelineRequest,
        CreativeTimelineStatus,
        MediaPreviewActivityRequest,
        NarrationReviewActivityRequest,
        RhythmPlanningActivityRequest,
        VisualPlanningActivityRequest,
    )

STAGE_TIMEOUT = timedelta(minutes=15)
HEARTBEAT_TIMEOUT = timedelta(seconds=30)


@workflow.defn
class CreativeTimelineWorkflow:
    def __init__(self) -> None:
        self._status: CreativeTimelineStatus | None = None
        self._decisions: dict[str, ReviewSignal] = {}

    def _retry(self) -> RetryPolicy:
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_attempts=3,
            non_retryable_error_types=["InvalidInput", "RightsBlocked"],
        )

    def _blocked(self, codes: tuple[str, ...]) -> CreativeTimelineStatus:
        if self._status is None:
            raise RuntimeError("workflow status is unavailable")
        self._status.state = "blocked"
        self._status.blocked_codes = codes
        return self._status

    @workflow.run
    async def run(self, request: CreativeTimelineRequest) -> CreativeTimelineStatus:
        self._status = CreativeTimelineStatus(run_id=request.run_id, state="running")
        self._status.stage_states["visual"] = "running"
        visual = await workflow.execute_activity(
            plan_visual_activity,
            VisualPlanningActivityRequest(
                run_id=request.run_id,
                project_id=request.project_id,
                trace_id=request.trace_id,
                resource_profile=request.resource_profile,
                beat_graph=request.beat_graph,
                candidate_sets=request.candidate_sets,
                queries=request.queries,
                source_durations=request.source_durations,
                ids=request.planning,
            ),
            start_to_close_timeout=STAGE_TIMEOUT,
            heartbeat_timeout=HEARTBEAT_TIMEOUT,
            retry_policy=self._retry(),
        )
        if visual.incomplete:
            self._status.stage_states["visual"] = "incomplete"
            return self._blocked(("coverage-incomplete",))
        self._status.stage_states["visual"] = "succeeded"
        self._status.artifacts.update(
            {
                "candidate_set": visual.candidate_set,
                "selection_plan": visual.selection_plan,
                "continuity_report": visual.continuity_report,
                "visual_report": visual.visual_report,
            }
        )

        self._status.stage_states["rhythm"] = "running"
        rhythm = await workflow.execute_activity(
            plan_rhythm_activity,
            RhythmPlanningActivityRequest(
                run_id=request.run_id,
                project_id=request.project_id,
                trace_id=request.trace_id,
                resource_profile=request.resource_profile,
                beat_graph=request.beat_graph,
                selection_plan=visual.selection_plan,
                rhythm_plan_id=request.rhythm_plan_id,
            ),
            start_to_close_timeout=STAGE_TIMEOUT,
            heartbeat_timeout=HEARTBEAT_TIMEOUT,
            retry_policy=self._retry(),
        )
        if rhythm.rhythm_plan is None:
            self._status.stage_states["rhythm"] = "infeasible"
            return self._blocked(("duration-infeasible",))
        self._status.stage_states["rhythm"] = "succeeded"
        self._status.artifacts["rhythm_plan"] = rhythm.rhythm_plan

        self._status.stage_states["narration"] = "running"
        narration = await workflow.execute_activity(
            review_narration_activity,
            NarrationReviewActivityRequest(
                run_id=request.run_id,
                project_id=request.project_id,
                trace_id=request.trace_id,
                resource_profile=request.resource_profile,
                line_set=request.line_set,
                report_id=request.narration_report_id,
                dialogue_by_beat=request.dialogue_by_beat,
            ),
            start_to_close_timeout=STAGE_TIMEOUT,
            heartbeat_timeout=HEARTBEAT_TIMEOUT,
            retry_policy=self._retry(),
        )
        if narration.blocker_codes:
            self._status.stage_states["narration"] = "blocked"
            return self._blocked(narration.blocker_codes)
        self._status.stage_states["narration"] = "succeeded"
        self._status.artifacts["narration_report"] = narration.report

        self._status.stage_states["assembly"] = "running"
        assembly = await workflow.execute_activity(
            assemble_timeline_activity,
            AssemblyActivityRequest(
                run_id=request.run_id,
                project_id=request.project_id,
                trace_id=request.trace_id,
                resource_profile=request.resource_profile,
                selection_plan=visual.selection_plan,
                candidate_sets=request.candidate_sets,
                line_set=request.line_set,
                subtitle_style=request.subtitle_style,
                timeline_id=request.timeline_id,
                master_timeline_id=request.master_timeline_id,
                report_id=request.assembly_report_id,
                track_ids=request.track_ids,
                item_ids=request.item_ids,
            ),
            start_to_close_timeout=STAGE_TIMEOUT,
            heartbeat_timeout=HEARTBEAT_TIMEOUT,
            retry_policy=self._retry(),
        )
        if assembly.blocked or assembly.master_timeline is None:
            self._status.stage_states["assembly"] = "blocked"
            return self._blocked(assembly.conflict_codes)
        self._status.stage_states["assembly"] = "succeeded"
        self._status.artifacts["master_timeline"] = assembly.master_timeline
        self._status.artifacts["assembly_report"] = assembly.report

        self._status.stage_states["preview"] = "running"
        preview = await workflow.execute_activity(
            render_media_preview_activity,
            MediaPreviewActivityRequest(
                run_id=request.run_id,
                project_id=request.project_id,
                trace_id=request.trace_id,
                resource_profile=request.resource_profile,
                timeline=assembly.master_timeline,
                output_path=request.output_path,
            ),
            start_to_close_timeout=STAGE_TIMEOUT,
            heartbeat_timeout=HEARTBEAT_TIMEOUT,
            retry_policy=self._retry(),
        )
        self._status.stage_states["preview"] = "succeeded"
        self._status.artifacts["preview"] = preview.preview

        review_id = f"review:{request.run_id}:timeline"
        self._status.active_review_id = review_id
        self._status.state = "awaiting_review"
        await workflow.wait_condition(lambda: self._review_ready(review_id))
        self._status.active_review_id = None
        decision = self._decisions[review_id]
        self._status.state = "succeeded" if decision.decision == "approve" else decision.decision
        return self._status

    def _review_ready(self, review_id: str) -> bool:
        return review_id in self._decisions or (
            self._status is not None and self._status.state == "cancelled"
        )

    @workflow.signal
    def submit_review_decision(self, signal: ReviewSignal) -> None:
        if signal.review_id not in self._decisions:
            self._decisions[signal.review_id] = signal

    @workflow.signal
    def request_cancel(self) -> None:
        if self._status is not None:
            self._status.state = "cancelled"

    @workflow.query
    def get_status(self) -> CreativeTimelineStatus | None:
        return self._status
