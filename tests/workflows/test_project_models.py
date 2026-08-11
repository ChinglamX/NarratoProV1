from workflows.project.models import (
    ArtifactPointer,
    ProjectRunInput,
    ProjectRunStatus,
    ReviewSignal,
)
from workflows.project.workflow import ProjectRunWorkflow


def test_workflow_history_payload_is_small_and_pointer_based() -> None:
    pointer = ArtifactPointer("artifact", 1, "ConfigSnapshot", "sha256:value")
    request = ProjectRunInput("run", "project", "a" * 32, pointer, pointer, pointer)
    assert request.config_snapshot is pointer
    assert request.stages == ("foundation-conformance",)


def test_run_status_tracks_graph_and_stage_state() -> None:
    status = ProjectRunStatus("run", "running")
    status.stage_states["fact"] = "awaiting_review"
    assert status.graph_version == 1
    assert status.stage_states == {"fact": "awaiting_review"}


def test_workflow_signals_are_first_wins_and_cancel_is_queryable() -> None:
    workflow = ProjectRunWorkflow()
    workflow._status = ProjectRunStatus("run", "awaiting_review")
    first = ReviewSignal("review", 1, "approve")
    workflow.submit_review_decision(first)
    workflow.submit_review_decision(ReviewSignal("review", 1, "reject"))
    assert workflow._review_ready("review")
    assert workflow._review_signals["review"] is first
    workflow.request_cancel()
    assert workflow.get_run_status() is not None
    assert workflow.get_run_status().cancel_requested is True
