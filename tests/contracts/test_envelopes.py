import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    ActorRef,
    CommandEnvelope,
    ErrorDetail,
    ErrorEnvelope,
    EventEnvelope,
)
from packages.contracts.envelopes import public_contract_shape

TRACE_ID = "0123456789abcdef0123456789abcdef"


def command() -> CommandEnvelope:
    return CommandEnvelope(
        command_id=uuid4(),
        command_type="project.create",
        schema_version="1.0.0",
        project_id=uuid4(),
        actor=ActorRef(kind="human", id="reviewer:42"),
        idempotency_key="client:project:create:001",
        payload={"title": "年代短剧", "episodes": 12},
        requested_at=datetime(2026, 8, 11, tzinfo=UTC),
    )


def event() -> EventEnvelope:
    project_id = uuid4()
    return EventEnvelope(
        event_id=uuid4(),
        event_type="project.created",
        schema_version="1.0.0",
        aggregate_id=str(project_id),
        aggregate_version=1,
        project_id=project_id,
        occurred_at=datetime(2026, 8, 11, tzinfo=UTC),
        producer="control.project-service",
        trace_id=TRACE_ID,
        payload={"project_id": str(project_id)},
    )


@pytest.mark.parametrize("factory", [command, event])
def test_envelopes_have_canonical_json_round_trip(factory: object) -> None:
    envelope = factory()  # type: ignore[operator]
    restored = type(envelope).model_validate_json(envelope.canonical_json())
    assert restored == envelope
    assert restored.canonical_bytes() == envelope.canonical_bytes()


def test_command_requires_stable_idempotency_and_utc_time() -> None:
    values = command().model_dump()
    values["idempotency_key"] = "short"
    with pytest.raises(ValidationError):
        CommandEnvelope.model_validate(values)
    values = command().model_dump()
    values["requested_at"] = datetime(2026, 8, 11)
    with pytest.raises(ValidationError, match="must use UTC"):
        CommandEnvelope.model_validate(values)


@pytest.mark.parametrize(
    "trace_id",
    ["0" * 32, "ABCDEF0123456789ABCDEF0123456789", "0123", "g" * 32],
)
def test_event_rejects_invalid_trace_ids(trace_id: str) -> None:
    values = event().model_dump()
    values["trace_id"] = trace_id
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(values)


def test_payload_rejects_non_json_provider_objects() -> None:
    values = command().model_dump()
    values["payload"] = {"raw": object()}
    with pytest.raises(ValidationError):
        CommandEnvelope.model_validate(values)


def test_public_error_projection_redacts_internal_diagnostics() -> None:
    error = ErrorEnvelope(
        code="PROVIDER_TIMEOUT",
        category="provider",
        message="The provider did not respond in time.",
        retryable=True,
        details=(
            ErrorDetail(
                code="RETRY_AFTER",
                message="Retry after the operation backoff.",
                visibility="public",
            ),
            ErrorDetail(
                code="PROVIDER_RAW_RESPONSE",
                message="Internal provider response.",
                data={"signed_url": "https://secret.invalid/token=secret"},
            ),
        ),
        request_id="request:provider:0001",
        trace_id=TRACE_ID,
        remediation="Retry the operation later.",
        internal_message="/Users/operator/private/model.py: token=secret",
    )
    public_json = error.to_public().canonical_json()
    assert "RETRY_AFTER" in public_json
    for secret in ("PROVIDER_RAW_RESPONSE", "signed_url", "secret.invalid", "/Users/"):
        assert secret not in public_json


def test_public_detail_cannot_carry_unreviewed_structured_data() -> None:
    with pytest.raises(ValidationError, match="cannot carry"):
        ErrorDetail(
            code="INVALID_FIELD",
            message="A field is invalid.",
            visibility="public",
            data={"path": "/private/input.json"},
        )


def test_public_contract_shape_matches_breaking_change_snapshot() -> None:
    snapshot = json.loads(
        Path("tests/contracts/snapshots/b03_public_contract_shape.json").read_text()
    )
    assert public_contract_shape() == snapshot
