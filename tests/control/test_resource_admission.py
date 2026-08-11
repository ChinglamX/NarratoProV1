from datetime import UTC, datetime, timedelta

from packages.control.resource_admission import (
    ResourceAdmissionController,
    ResourceCapacity,
    ResourceRequest,
)


def _controller() -> ResourceAdmissionController:
    return ResourceAdmissionController(
        {
            "cpu": ResourceCapacity(
                cpu=4,
                memory_bytes=8_000,
                gpu=0,
                disk_bytes=10_000,
                cost_budget_micros=100,
                max_project_in_flight=2,
            )
        }
    )


def test_admission_enforces_capacity_and_is_idempotent() -> None:
    controller = _controller()
    request = ResourceRequest("p1", "cpu", cpu=2, memory_bytes=2_000)
    first = controller.admit(request, lease_id="one")
    repeated = controller.admit(request, lease_id="one")
    blocked = controller.admit(ResourceRequest("p2", "cpu", cpu=3), lease_id="two")
    assert first.admitted and first.lease is not None
    assert repeated.reason == "idempotent"
    assert not blocked.admitted and blocked.reason == "cpu_capacity"


def test_admission_fails_closed_and_recovers_expired_lease() -> None:
    controller = _controller()
    now = datetime(2026, 8, 12, tzinfo=UTC)
    unknown = controller.admit(ResourceRequest("p", "missing"), lease_id="bad", now=now)
    controller.admit(
        ResourceRequest("p", "cpu", cpu=4),
        lease_id="expiring",
        now=now,
        ttl=timedelta(seconds=1),
    )
    recovered = controller.admit(
        ResourceRequest("other", "cpu", cpu=4),
        lease_id="replacement",
        now=now + timedelta(seconds=2),
    )
    assert not unknown.admitted and unknown.reason == "unknown_queue"
    assert recovered.admitted


def test_project_fairness_limit_and_release() -> None:
    controller = _controller()
    for index in range(2):
        assert controller.admit(ResourceRequest("p", "cpu", cpu=1), lease_id=str(index)).admitted
    blocked = controller.admit(ResourceRequest("p", "cpu"), lease_id="third")
    assert blocked.reason == "project_in_flight_limit"
    assert controller.release("0")
    assert controller.admit(ResourceRequest("p", "cpu"), lease_id="third").admitted


def test_lease_conflict_cost_limit_and_active_listing() -> None:
    controller = _controller()
    assert controller.admit(
        ResourceRequest("p", "cpu", estimated_cost_micros=100), lease_id="same"
    ).admitted
    conflict = controller.admit(ResourceRequest("other", "cpu"), lease_id="same")
    blocked = controller.admit(
        ResourceRequest("other", "cpu", estimated_cost_micros=1), lease_id="cost"
    )
    assert conflict.reason == "lease_id_conflict"
    assert blocked.reason == "cost_budget"
    assert [lease.lease_id for lease in controller.active_leases()] == ["same"]
