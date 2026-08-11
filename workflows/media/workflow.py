"""Durable media ingest followed by mandatory Catalog review at L1."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.media.activities import ingest_media_activity
    from workflows.media.models import MediaIngestWorkflowInput, MediaIngestWorkflowStatus
    from workflows.project.models import ReviewSignal


@workflow.defn
class MediaIngestWorkflow:
    def __init__(self) -> None:
        self._status: MediaIngestWorkflowStatus | None = None
        self._decisions: dict[str, ReviewSignal] = {}

    @workflow.run
    async def run(self, request: MediaIngestWorkflowInput) -> MediaIngestWorkflowStatus:
        self._status = MediaIngestWorkflowStatus(request.run_id, "ingesting")
        result = await workflow.execute_activity(
            ingest_media_activity,
            request,
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        self._status.source = result.source
        self._status.catalog = result.catalog
        review_id = f"review:{request.run_id}:media-catalog"
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
    def status(self) -> MediaIngestWorkflowStatus | None:
        return self._status
