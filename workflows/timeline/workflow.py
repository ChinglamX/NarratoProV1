"""Durable fake media-to-preview workflow with mandatory human checkpoint."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.project.models import ReviewSignal
    from workflows.timeline.activities import render_preview_activity
    from workflows.timeline.models import PreviewWorkflowInput, PreviewWorkflowStatus


@workflow.defn
class TimelinePreviewWorkflow:
    def __init__(self) -> None:
        self._status: PreviewWorkflowStatus | None = None
        self._decisions: dict[str, ReviewSignal] = {}

    @workflow.run
    async def run(self, request: PreviewWorkflowInput) -> PreviewWorkflowStatus:
        self._status = PreviewWorkflowStatus(request.run_id, "rendering")
        result = await workflow.execute_activity(
            render_preview_activity,
            request,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
        self._status.preview = result.preview
        review_id = f"review:{request.run_id}:timeline-preview"
        self._status.active_review_id = review_id
        self._status.state = "awaiting_review"
        await workflow.wait_condition(lambda: review_id in self._decisions)
        decision = self._decisions[review_id]
        self._status.active_review_id = None
        self._status.state = "succeeded" if decision.decision == "approve" else decision.decision
        return self._status

    @workflow.signal
    def submit_review(self, signal: ReviewSignal) -> None:
        if signal.review_id not in self._decisions:
            self._decisions[signal.review_id] = signal

    @workflow.query
    def status(self) -> PreviewWorkflowStatus | None:
        return self._status
