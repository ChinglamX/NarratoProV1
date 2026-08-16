"""E11 render workflow: execute ffmpeg plan then technical QC."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from workflows.production.models import MediaProductionPlanningStatus  # noqa: F401
    from workflows.production.render_activities import (
        RenderRequest,
        RenderResult,
        execute_render_activity,
        technical_qc_activity,
    )


@workflow.defn
class RenderWorkflow:  # pragma: no cover - verified by real Temporal run
    def __init__(self) -> None:
        self._status: RenderResult | None = None

    @workflow.run
    async def run(self, request: RenderRequest) -> RenderResult:  # pragma: no cover
        retry = RetryPolicy(maximum_attempts=3, non_retryable_error_types=["RuntimeError"])
        execution: object = await workflow.execute_activity(
            execute_render_activity,
            request,
            start_to_close_timeout=timedelta(minutes=60),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        qc: object = await workflow.execute_activity(
            technical_qc_activity,
            request,
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=retry,
        )
        from typing import cast

        from workflows.project.models import ArtifactPointer

        result = RenderResult(
            execution_report=cast(ArtifactPointer, execution),
            qc_report=cast(ArtifactPointer, qc),
            output_path=request.output_path,
            passed=not getattr(qc, "blocked_codes", ()),
        )
        self._status = result
        return result

    @workflow.query
    def status(self) -> RenderResult | None:  # pragma: no cover
        return self._status
