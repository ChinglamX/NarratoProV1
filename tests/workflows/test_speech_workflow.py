from workflows.speech.models import SpeechWorkflowStatus
from workflows.speech.workflow import SpeechObservationWorkflow


def test_speech_workflow_status_is_queryable() -> None:
    workflow = SpeechObservationWorkflow()
    workflow._status = SpeechWorkflowStatus("run", "processing")
    assert workflow.status() is workflow._status
