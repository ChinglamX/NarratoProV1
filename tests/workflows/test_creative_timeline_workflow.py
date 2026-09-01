"""CreativeTimelineWorkflow unit tests: signals, fail-closed blocking, queries."""

from workflows.project.models import ArtifactPointer, ReviewSignal
from workflows.timeline.creative_models import CreativeTimelineStatus
from workflows.timeline.creative_workflow import CreativeTimelineWorkflow


def test_review_decision_is_first_wins_and_status_queryable() -> None:
    value = CreativeTimelineWorkflow()
    value._status = CreativeTimelineStatus(
        "run",
        "awaiting_review",
        stage_states={"preview": "succeeded"},
        active_review_id="review:run:timeline",
        artifacts={
            "master_timeline": ArtifactPointer("t", 1, "MasterTimeline", "sha256:" + "0" * 64)
        },
    )
    first = ReviewSignal("review:run:timeline", 1, "approve")
    value.submit_review_decision(first)
    value.submit_review_decision(ReviewSignal("review:run:timeline", 1, "reject"))
    assert value._decisions["review:run:timeline"] is first
    assert value.get_status() is value._status


def test_blocked_helper_marks_state_and_codes() -> None:
    value = CreativeTimelineWorkflow()
    value._status = CreativeTimelineStatus("run", "running")
    status = value._blocked(("coverage-incomplete",))
    assert status.state == "blocked"
    assert status.blocked_codes == ("coverage-incomplete",)


def test_cancel_signal_flips_state() -> None:
    value = CreativeTimelineWorkflow()
    value._status = CreativeTimelineStatus("run", "awaiting_review")
    value.request_cancel()
    assert value.get_status() is not None and value.get_status().state == "cancelled"
