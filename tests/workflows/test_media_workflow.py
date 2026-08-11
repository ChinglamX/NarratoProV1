from workflows.media.models import MediaIngestWorkflowStatus
from workflows.media.workflow import MediaIngestWorkflow
from workflows.project.models import ReviewSignal


def test_media_workflow_review_signal_is_first_wins() -> None:
    value = MediaIngestWorkflow()
    value._status = MediaIngestWorkflowStatus("run", "awaiting_review", active_review_id="r")
    first = ReviewSignal("r", 1, "approve")
    value.submit_review(first)
    value.submit_review(ReviewSignal("r", 1, "reject"))
    assert value._decisions["r"] is first
    assert value.status() is value._status
