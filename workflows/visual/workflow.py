from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.visual.activities import process_visual_activity
    from workflows.visual.models import VisualWorkflowInput, VisualWorkflowStatus


@workflow.defn
class VisualObservationWorkflow:
    def __init__(self) -> None:
        self._status: VisualWorkflowStatus | None = None

    @workflow.run
    async def run(self, request: VisualWorkflowInput) -> VisualWorkflowStatus:
        self._status = VisualWorkflowStatus(request.run_id, "processing")
        result = await workflow.execute_activity(
            process_visual_activity,
            request,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        self._status.raw_response = result.raw_response
        self._status.observation = result.observation
        self._status.state = "succeeded"
        return self._status

    @workflow.query
    def status(self) -> VisualWorkflowStatus | None:
        return self._status
