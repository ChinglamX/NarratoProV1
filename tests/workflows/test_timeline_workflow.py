from workflows.project.models import ArtifactPointer, ReviewSignal
from workflows.timeline.models import PreviewWorkflowStatus
from workflows.timeline.workflow import TimelinePreviewWorkflow


def test_preview_workflow_signal_is_first_wins_and_status_queryable() -> None:
    workflow = TimelinePreviewWorkflow()
    workflow._status = PreviewWorkflowStatus(
        "run", "awaiting_review", ArtifactPointer("preview", 1, "ProxyRender"), "review"
    )
    first = ReviewSignal("review", 1, "approve")
    workflow.submit_review(first)
    workflow.submit_review(ReviewSignal("review", 1, "reject"))
    assert workflow._decisions["review"] is first
    assert workflow.status() is workflow._status
