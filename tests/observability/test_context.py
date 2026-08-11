import pytest

from packages.observability import MetricPoint, TraceContext, redact


def test_trace_context_omits_absent_dimensions() -> None:
    assert TraceContext("a" * 32, project_id="p").log_fields() == {
        "trace_id": "a" * 32,
        "project_id": "p",
    }


def test_redaction_is_recursive() -> None:
    assert redact({"token": "bad", "nested": [{"password": "bad", "ok": 1}]}) == {
        "token": "[REDACTED]",
        "nested": [{"password": "[REDACTED]", "ok": 1}],
    }
    assert redact(({"api_key": "bad"},)) == ({"api_key": "[REDACTED]"},)


def test_metrics_reject_high_cardinality_labels() -> None:
    MetricPoint("workflow_stage_total", 1, {"stage": "story", "state": "succeeded"})
    with pytest.raises(ValueError):
        MetricPoint("workflow_stage_total", 1, {"project_id": "unique"})
