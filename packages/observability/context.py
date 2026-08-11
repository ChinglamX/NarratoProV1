"""Low-cardinality trace context and recursive secret redaction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_SECRET_KEYS = {"authorization", "password", "secret", "token", "api_key"}


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    project_id: str | None = None
    run_id: str | None = None
    stage: str | None = None

    def log_fields(self) -> dict[str, str]:
        values = {
            "trace_id": self.trace_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "stage": self.stage,
        }
        return {key: value for key, value in values.items() if value is not None}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if str(key).lower() in _SECRET_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value
