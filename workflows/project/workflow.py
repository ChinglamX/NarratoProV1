"""Replay-safe E03 ProjectRunWorkflow skeleton with human wait/resume."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.project.activities import execute_conformance_activity
    from workflows.project.models import (
        ActivityRequest,
        ProjectRunInput,
        ProjectRunStatus,
        ReviewSignal,
    )


@workflow.defn
class ProjectRunWorkflow:
    def __init__(self) -> None:
        self._status: ProjectRunStatus | None = None
        self._review_signals: dict[str, ReviewSignal] = {}

    @workflow.run
    async def run(self, request: ProjectRunInput) -> ProjectRunStatus:
        self._status = ProjectRunStatus(run_id=request.run_id, state="running")
        for index, stage in enumerate(request.stages):
            if self._status.cancel_requested:
                self._status.state = "cancelled"
                return self._status
            self._status.stage_states[stage] = "running"
            result = await workflow.execute_activity(
                execute_conformance_activity,
                ActivityRequest(
                    activity_id=f"{request.run_id}-{index}",
                    run_id=request.run_id,
                    trace_id=request.trace_id,
                    stage=stage,
                    execution_key=f"{request.run_id}:{stage}:{index}",
                    inputs=tuple(self._status.current_artifacts.values()),
                    config_snapshot=request.config_snapshot,
                    output_contract="ConfigArtifact",
                    resource_requirement={"queue": "maintenance", "memory_bytes": 1},
                ),
                start_to_close_timeout=timedelta(seconds=30),
                heartbeat_timeout=timedelta(seconds=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(milliseconds=100),
                    maximum_attempts=3,
                    non_retryable_error_types=["InvalidInput", "RightsBlocked"],
                ),
            )
            self._status.current_artifacts[stage] = result.outputs[0]
            self._status.stage_states[stage] = "awaiting_review"
            review_id = f"review:{request.run_id}:{stage}"
            self._status.active_review_id = review_id
            self._status.state = "awaiting_review"
            await workflow.wait_condition(lambda: self._review_ready(review_id))  # noqa: B023
            if self._status.cancel_requested:
                self._status.state = "cancelled"
                return self._status
            decision = self._review_signals[review_id]
            if decision.target_version != result.outputs[0].version:
                self._status.stage_states[stage] = "stale_review"
                self._status.state = "failed"
                return self._status
            if decision.decision == "reject":
                self._status.stage_states[stage] = "rejected"
                self._status.state = "rejected"
                return self._status
            if decision.decision == "revise":
                self._status.graph_version += 1
                self._status.stage_states[stage] = "revision_required"
                self._status.state = "revision_required"
                return self._status
            self._status.stage_states[stage] = "succeeded"
            self._status.active_review_id = None
            self._status.state = "running"
        self._status.state = "succeeded"
        return self._status

    @workflow.signal
    def submit_review_decision(self, signal: ReviewSignal) -> None:
        existing = self._review_signals.get(signal.review_id)
        if existing is None:
            self._review_signals[signal.review_id] = signal

    @workflow.signal
    def request_cancel(self) -> None:
        if self._status is not None:
            self._status.cancel_requested = True

    @workflow.query
    def get_run_status(self) -> ProjectRunStatus | None:
        return self._status

    def _review_ready(self, review_id: str) -> bool:
        return review_id in self._review_signals or (
            self._status is not None and self._status.cancel_requested
        )
