"""E03 conformance activities; real domain activities replace these incrementally."""

from __future__ import annotations

from temporalio import activity
from temporalio.exceptions import ApplicationError

from workflows.project.models import ActivityRequest, ActivityResult, ArtifactPointer


@activity.defn
async def execute_conformance_activity(request: ActivityRequest) -> ActivityResult:
    activity.heartbeat({"execution_key": request.execution_key, "cursor": "started"})
    if request.stage == "invalid-input":
        raise ApplicationError("invalid conformance input", non_retryable=True, type="InvalidInput")
    if request.stage == "transient-once" and activity.info().attempt == 1:
        raise ApplicationError("injected transient failure", type="RetryableTransient")
    output = ArtifactPointer(
        artifact_id=request.activity_id,
        version=1,
        artifact_type=request.output_contract,
    )
    activity.heartbeat({"execution_key": request.execution_key, "cursor": "completed"})
    return ActivityResult(
        execution_key=request.execution_key,
        outputs=(output,),
        metrics={"attempt": activity.info().attempt},
    )
