"""Deterministic resource admission with bounded, recoverable leases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    project_id: str
    queue: str
    cpu: int = 0
    memory_bytes: int = 0
    gpu: int = 0
    disk_bytes: int = 0
    estimated_cost_micros: int = 0


@dataclass(frozen=True, slots=True)
class ResourceCapacity:
    cpu: int
    memory_bytes: int
    gpu: int
    disk_bytes: int
    cost_budget_micros: int
    max_project_in_flight: int


@dataclass(frozen=True, slots=True)
class ResourceLease:
    lease_id: str
    request: ResourceRequest
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    admitted: bool
    reason: str
    lease: ResourceLease | None = None


class ResourceAdmissionController:
    """Admission is atomic per process and fails closed for unknown queues."""

    def __init__(self, capacities: dict[str, ResourceCapacity]) -> None:
        self._capacities = capacities.copy()
        self._leases: dict[str, ResourceLease] = {}
        self._lock = Lock()

    def admit(
        self,
        request: ResourceRequest,
        *,
        lease_id: str,
        now: datetime | None = None,
        ttl: timedelta = timedelta(minutes=5),
    ) -> AdmissionDecision:
        instant = now or datetime.now(UTC)
        with self._lock:
            self._expire(instant)
            existing = self._leases.get(lease_id)
            if existing is not None:
                if existing.request == request:
                    return AdmissionDecision(True, "idempotent", existing)
                return AdmissionDecision(False, "lease_id_conflict")
            capacity = self._capacities.get(request.queue)
            if capacity is None:
                return AdmissionDecision(False, "unknown_queue")
            active = [lease.request for lease in self._leases.values()]
            if sum(item.project_id == request.project_id for item in active) >= (
                capacity.max_project_in_flight
            ):
                return AdmissionDecision(False, "project_in_flight_limit")
            queue_active = [item for item in active if item.queue == request.queue]
            limits = (
                (
                    sum(item.cpu for item in queue_active) + request.cpu,
                    capacity.cpu,
                    "cpu_capacity",
                ),
                (
                    sum(item.memory_bytes for item in queue_active) + request.memory_bytes,
                    capacity.memory_bytes,
                    "memory_capacity",
                ),
                (
                    sum(item.gpu for item in queue_active) + request.gpu,
                    capacity.gpu,
                    "gpu_capacity",
                ),
                (
                    sum(item.disk_bytes for item in queue_active) + request.disk_bytes,
                    capacity.disk_bytes,
                    "disk_capacity",
                ),
                (
                    sum(item.estimated_cost_micros for item in queue_active)
                    + request.estimated_cost_micros,
                    capacity.cost_budget_micros,
                    "cost_budget",
                ),
            )
            for used, maximum, reason in limits:
                if used > maximum:
                    return AdmissionDecision(False, reason)
            lease = ResourceLease(lease_id, request, instant + ttl)
            self._leases[lease_id] = lease
            return AdmissionDecision(True, "admitted", lease)

    def release(self, lease_id: str) -> bool:
        with self._lock:
            return self._leases.pop(lease_id, None) is not None

    def active_leases(self, *, now: datetime | None = None) -> tuple[ResourceLease, ...]:
        with self._lock:
            self._expire(now or datetime.now(UTC))
            return tuple(sorted(self._leases.values(), key=lambda lease: lease.lease_id))

    def _expire(self, now: datetime) -> None:
        expired = [key for key, lease in self._leases.items() if lease.expires_at <= now]
        for key in expired:
            del self._leases[key]
