from dataclasses import replace
from uuid import uuid4

import pytest

from packages.contracts import (
    ProviderInvocationRequest,
    ProviderPackage,
    ProviderResourceEstimate,
)
from packages.providers import (
    InvocationPolicy,
    ProviderGateway,
    ProviderPolicyError,
    ProviderRawOutput,
)


class FakeProvider:
    def __init__(self, package: ProviderPackage, *, healthy: bool = True) -> None:
        self.value = package
        self.healthy = healthy
        self.validated = False

    def package(self) -> ProviderPackage:
        return self.value

    def validate(self, _request: ProviderInvocationRequest) -> None:
        self.validated = True

    def estimate(self, _request: ProviderInvocationRequest) -> ProviderResourceEstimate:
        return ProviderResourceEstimate(
            cpu_cores=2,
            memory_bytes=100,
            estimated_duration_ms=10,
            estimated_cost_micros=0,
        )

    def infer(self, _request: ProviderInvocationRequest) -> ProviderRawOutput:
        return ProviderRawOutput(b"{}", "application/json", "1", 10, 0)

    def health(self) -> bool:
        return self.healthy


def package(*, admission: str = "production", location: str = "local") -> ProviderPackage:
    return ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "local",
                "implementation": "fake",
                "version": "1",
                "license": "Apache-2.0",
            },
            "capabilities": ["asr"],
            "admission": admission,
            "code_license": "Apache-2.0",
            "commercial_use_allowed": admission == "production",
            "data_policy": {
                "execution_location": location,
                "allowed_residencies": ["CN"],
                "transmits_source_media": location == "external_cloud",
                "retains_input": False,
            },
            "supported_hardware": ["cpu"],
            "deterministic": True,
            "retry_safe": True,
            "max_batch_size": 1,
        }
    )


def request() -> ProviderInvocationRequest:
    return ProviderInvocationRequest.model_validate(
        {
            "capability": "asr",
            "inputs": [{"artifact_id": uuid4(), "version": 1, "artifact_type": "AudioStem"}],
            "config_ref": {
                "artifact_id": uuid4(),
                "version": 1,
                "artifact_type": "ConfigArtifact",
            },
            "resource_profile_ref": {
                "artifact_id": uuid4(),
                "version": 1,
                "artifact_type": "ResourceProfile",
            },
            "idempotency_key": "asr:one",
            "timeout_ms": 1000,
        }
    )


def policy(**overrides: object) -> InvocationPolicy:
    value = InvocationPolicy(False, False, "CN", 0, 1000, 0)
    return replace(value, **overrides)


def test_gateway_admits_matching_production_provider() -> None:
    provider = FakeProvider(package())
    result = ProviderGateway().invoke(provider, request(), policy())
    assert provider.validated and result.payload == b"{}"


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        (FakeProvider(package(admission="blocked")), "blocked"),
        (FakeProvider(package(admission="research")), "research"),
        (FakeProvider(package(location="external_cloud")), "external cloud"),
        (FakeProvider(package(), healthy=False), "unavailable"),
    ],
)
def test_gateway_policy_is_fail_closed(provider: FakeProvider, expected: str) -> None:
    with pytest.raises(ProviderPolicyError, match=expected):
        ProviderGateway().invoke(provider, request(), policy())
