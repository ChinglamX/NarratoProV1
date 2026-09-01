"""Media ingest workflow exports."""

from temporalio import workflow

# The media ingest activity chain imports PySceneDetect -> OpenCV -> numpy,
# whose C extensions cannot be loaded twice in one process. Loading them
# outside the workflow sandbox keeps the default sandbox protection for
# workflow code while avoiding the duplicate-import crash.
with workflow.unsafe.imports_passed_through():
    from workflows.media.activities import ingest_media_activity
from workflows.media.workflow import MediaIngestWorkflow

__all__ = ["MediaIngestWorkflow", "ingest_media_activity"]
