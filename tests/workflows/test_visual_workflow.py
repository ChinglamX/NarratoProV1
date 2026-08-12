from workflows.visual.models import VisualWorkflowStatus
from workflows.visual.workflow import VisualObservationWorkflow


def test_visual_workflow_status_is_queryable() -> None:
    workflow = VisualObservationWorkflow()
    workflow._status = VisualWorkflowStatus("run", "processing")
    assert workflow.status() is workflow._status
