from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.speech.activities import process_speech_activity
    from workflows.speech.models import SpeechWorkflowInput, SpeechWorkflowStatus


@workflow.defn
class SpeechObservationWorkflow:
    def __init__(self) -> None:
        self._status: SpeechWorkflowStatus | None = None

    @workflow.run
    async def run(self, request: SpeechWorkflowInput) -> SpeechWorkflowStatus:
        self._status = SpeechWorkflowStatus(request.run_id, "processing")
        result = await workflow.execute_activity(
            process_speech_activity,
            request,
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        self._status.raw_response = result.raw_response
        self._status.observation = result.observation
        self._status.state = "succeeded"
        return self._status

    @workflow.query
    def status(self) -> SpeechWorkflowStatus | None:
        return self._status
