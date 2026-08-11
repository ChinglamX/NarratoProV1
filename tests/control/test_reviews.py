import pytest

from packages.control.reviews import (
    ReviewConflict,
    Reviewer,
    ReviewForbidden,
    ReviewGate,
    authorize_decision,
    validate_target,
)


def test_release_requires_human_release_approver() -> None:
    with pytest.raises(ReviewForbidden):
        authorize_decision(ReviewGate.RELEASE, Reviewer("robot", frozenset({"reviewer"})))
    with pytest.raises(ReviewForbidden):
        authorize_decision(
            ReviewGate.RELEASE,
            Reviewer("robot", frozenset({"release_approver"}), service_account=True),
        )
    authorize_decision(
        ReviewGate.RELEASE,
        Reviewer("human", frozenset({"release_approver"})),
    )


def test_non_release_gate_requires_reviewer() -> None:
    authorize_decision(ReviewGate.STORY, Reviewer("human", frozenset({"reviewer"})))
    with pytest.raises(ReviewForbidden):
        authorize_decision(ReviewGate.TIMELINE, Reviewer("viewer", frozenset({"viewer"})))


def test_target_version_and_state_are_optimistic_lock() -> None:
    validate_target(expected_version=2, actual_version=2, state="awaiting_review")
    with pytest.raises(ReviewConflict):
        validate_target(expected_version=1, actual_version=2, state="awaiting_review")
    with pytest.raises(ReviewConflict):
        validate_target(expected_version=2, actual_version=2, state="decided")
