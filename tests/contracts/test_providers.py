from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    ProviderDataPolicy,
    ProviderFailure,
    ProviderInvocationRequest,
    ProviderPackage,
)


def identity(*, model: str | None = "model") -> dict[str, object]:
    return {
        "provider": "local",
        "implementation": "fake-provider",
        "version": "1.0.0",
        "model": model,
        "checksum": "sha256:" + "a" * 64 if model else None,
        "license": "Apache-2.0",
    }


def data_policy(**overrides: object) -> ProviderDataPolicy:
    values: dict[str, object] = {
        "execution_location": "local",
        "allowed_residencies": ["CN"],
        "transmits_source_media": False,
        "retains_input": False,
    }
    values.update(overrides)
    return ProviderDataPolicy.model_validate(values)


def test_production_provider_requires_model_license_checksum_and_commercial_approval() -> None:
    package = ProviderPackage.model_validate(
        {
            "identity": identity(),
            "capabilities": ["asr"],
            "admission": "production",
            "code_license": "Apache-2.0",
            "weight_license": "Apache-2.0",
            "commercial_use_allowed": True,
            "model_checksum": "sha256:" + "a" * 64,
            "data_policy": data_policy(),
            "supported_hardware": ["cpu", "metal"],
            "supported_languages": ["zh-CN"],
            "deterministic": False,
            "retry_safe": True,
            "max_batch_size": 8,
        }
    )
    assert package.capabilities == ("asr",)
    with pytest.raises(ValidationError, match="commercial-use"):
        ProviderPackage.model_validate({**package.model_dump(), "commercial_use_allowed": False})
    with pytest.raises(ValidationError, match="weight license"):
        ProviderPackage.model_validate({**package.model_dump(), "weight_license": None})


def test_data_retention_and_failure_retry_semantics_fail_closed() -> None:
    with pytest.raises(ValidationError, match="retention_days"):
        data_policy(retains_input=True)
    with pytest.raises(ValidationError, match="cannot be retryable"):
        ProviderFailure(code="invalid_input", message="bad", retryable=True, unavailable=False)
    with pytest.raises(ValidationError, match="requires retryable"):
        ProviderFailure(
            code="provider_unavailable",
            message="down",
            retryable=False,
            unavailable=True,
            retry_after_ms=10,
        )


def test_provider_invocation_requires_exact_inputs() -> None:
    base = {
        "capability": "ocr",
        "inputs": [],
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
        "idempotency_key": "ocr:1",
        "timeout_ms": 1000,
    }
    with pytest.raises(ValidationError, match="requires inputs"):
        ProviderInvocationRequest.model_validate(base)
