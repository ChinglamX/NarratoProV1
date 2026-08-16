"""E10 media-production planning workflow (mix -> subtitle -> ASS)."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.production.activities import (
        BuildSubtitleInput,
        PlanMixInput,
        RenderAssInput,
        build_subtitle_activity,
        plan_mix_activity,
        render_ass_activity,
    )
    from workflows.production.models import (
        MediaProductionPlanningInput,
        MediaProductionPlanningStatus,
    )


@workflow.defn
class MediaProductionPlanningWorkflow:
    def __init__(self) -> None:
        self._status: MediaProductionPlanningStatus | None = None

    @workflow.run
    async def run(
        self, request: MediaProductionPlanningInput
    ) -> MediaProductionPlanningStatus:  # pragma: no cover
        if request.resource_profile is None:
            raise ValueError("media production planning requires a resource profile")
        self._status = MediaProductionPlanningStatus(request.run_id, "planning")
        retry = RetryPolicy(maximum_attempts=3, non_retryable_error_types=["ValueError"])

        mix_plan = await workflow.execute_activity(
            plan_mix_activity,
            PlanMixInput(
                project_id=request.project_id,
                run_id=request.run_id,
                trace_id=request.trace_id,
                timeline=request.timeline,
                narration_source=request.voice_asset or request.narration_line_set,
                style_profile=request.style_profile or request.resource_profile,
                resource_profile=request.resource_profile,
                mix_plan_id=request.mix_plan_id,
                target_loudness_lufs=request.target_loudness_lufs,
                true_peak_ceiling_dbtp=request.true_peak_ceiling_dbtp,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        self._status.mix_plan = mix_plan

        cue_set = await workflow.execute_activity(
            build_subtitle_activity,
            BuildSubtitleInput(
                project_id=request.project_id,
                run_id=request.run_id,
                trace_id=request.trace_id,
                narration_line_set=request.narration_line_set,
                style_profile=request.style_profile or request.resource_profile,
                resource_profile=request.resource_profile,
                cue_set_id=request.subtitle_cue_set_id,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        self._status.subtitle_cue_set = cue_set

        ass = await workflow.execute_activity(
            render_ass_activity,
            RenderAssInput(
                project_id=request.project_id,
                run_id=request.run_id,
                trace_id=request.trace_id,
                cue_set=cue_set,
                libass_profile=request.style_profile or request.resource_profile,
                resource_profile=request.resource_profile,
                ass_artifact_id=request.ass_artifact_id,
            ),
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        self._status.ass_artifact = ass
        self._status.tts_pending = request.voice_asset is None
        self._status.state = "succeeded"
        return self._status

    @workflow.query
    def status(self) -> MediaProductionPlanningStatus | None:
        return self._status
