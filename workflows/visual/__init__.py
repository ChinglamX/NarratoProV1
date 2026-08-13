"""Visual observation workflow exports."""

from temporalio import workflow

# The visual activity chain imports OpenCV -> numpy, whose C extensions cannot
# be loaded twice in one process. Load them outside the workflow sandbox.
with workflow.unsafe.imports_passed_through():
    from workflows.visual.activities import process_visual_activity
from workflows.visual.workflow import VisualObservationWorkflow

__all__ = ["VisualObservationWorkflow", "process_visual_activity"]
