"""Provider port and fail-closed policy gateway."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from packages.contracts.providers import (
    ExecutionLocation,
    ProviderAdmission,
    ProviderInvocationRequest,
    ProviderPackage,
    ProviderResourceEstimate,
)
from packages.providers.admission import ProviderAdmissionError, assert_production_ready


class ProviderPolicyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderRawOutput:
    payload: bytes
    media_type: str
    schema_version: str
    duration_ms: int
    cost_micros: int


class ProviderPort(Protocol):
    def package(self) -> ProviderPackage: ...

    def validate(self, request: ProviderInvocationRequest) -> None: ...

    def estimate(self, request: ProviderInvocationRequest) -> ProviderResourceEstimate: ...

    def infer(self, request: ProviderInvocationRequest) -> ProviderRawOutput: ...

    def health(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class InvocationPolicy:
    allow_research: bool
    allow_external_cloud: bool
    allowed_residency: str
    max_cost_micros: int
    max_memory_bytes: int
    max_accelerator_memory_bytes: int


class ProviderGateway:
    def invoke(
        self,
        provider: ProviderPort,
        request: ProviderInvocationRequest,
        policy: InvocationPolicy,
    ) -> ProviderRawOutput:
        package = provider.package()
        if request.capability not in package.capabilities:
            raise ProviderPolicyError("provider does not implement requested capability")
        if package.admission is ProviderAdmission.BLOCKED:
            raise ProviderPolicyError("provider is blocked")
        if package.admission is ProviderAdmission.PRODUCTION:
            # Fail-closed: a production package must carry full admission
            # evidence (model checksum, license, commercial approval).
            try:
                assert_production_ready(package)
            except ProviderAdmissionError as error:
                raise ProviderPolicyError(str(error)) from error
        if package.admission is ProviderAdmission.RESEARCH and not policy.allow_research:
            raise ProviderPolicyError("research provider is not permitted")
        if not package.commercial_use_allowed and not policy.allow_research:
            raise ProviderPolicyError("commercial use is not approved")
        if (
            package.data_policy.execution_location is ExecutionLocation.EXTERNAL_CLOUD
            and not policy.allow_external_cloud
        ):
            raise ProviderPolicyError("external cloud execution is not permitted")
        if policy.allowed_residency not in package.data_policy.allowed_residencies:
            raise ProviderPolicyError("provider data residency is not permitted")
        provider.validate(request)
        estimate = provider.estimate(request)
        if estimate.estimated_cost_micros > policy.max_cost_micros:
            raise ProviderPolicyError("provider estimate exceeds cost budget")
        if estimate.memory_bytes > policy.max_memory_bytes:
            raise ProviderPolicyError("provider estimate exceeds memory budget")
        if estimate.accelerator_memory_bytes > policy.max_accelerator_memory_bytes:
            raise ProviderPolicyError("provider estimate exceeds accelerator memory budget")
        if not provider.health():
            raise ProviderPolicyError("provider is unavailable")
        result = provider.infer(request)
        if not result.payload or not result.media_type or not result.schema_version:
            raise ProviderPolicyError("provider returned an empty raw response boundary")
        if result.cost_micros < 0 or result.duration_ms < 0:
            raise ProviderPolicyError("provider returned invalid invocation accounting")
        return result
