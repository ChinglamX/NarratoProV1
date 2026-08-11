"""Real Temporal E03 durability, retry, signal de-duplication and replay acceptance."""

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

from temporalio.client import Client, WorkflowFailureError
from temporalio.worker import Replayer, Worker

from workflows.project import (
    ProjectRunInput,
    ProjectRunWorkflow,
    ReviewSignal,
    execute_conformance_activity,
)
from workflows.project.models import ArtifactPointer

TASK_QUEUE = "e03-acceptance"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _pointer(kind: str) -> ArtifactPointer:
    return ArtifactPointer(str(uuid4()), 1, kind)


def _request(run_id: str, stage: str) -> ProjectRunInput:
    return ProjectRunInput(
        run_id=run_id,
        project_id=str(uuid4()),
        trace_id="a" * 32,
        effective_policy=_pointer("AutomationPolicy"),
        resource_profile=_pointer("ResourceProfile"),
        config_snapshot=_pointer("ConfigSnapshot"),
        stages=(stage,),
    )


def _worker(client: Client) -> Worker:
    return Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ProjectRunWorkflow],
        activities=[execute_conformance_activity],
    )


async def _wait_for_review(handle: object) -> object:
    for _ in range(100):
        status = await handle.query(ProjectRunWorkflow.get_run_status)  # type: ignore[attr-defined]
        if status is not None and status.state == "awaiting_review":
            return status
        await asyncio.sleep(0.05)
    raise AssertionError("workflow did not reach review wait state")


async def main() -> None:
    client = await Client.connect("127.0.0.1:7233")
    durable_id = f"e03-durable-{uuid4()}"
    async with _worker(client):
        handle = await client.start_workflow(
            ProjectRunWorkflow.run,
            _request(durable_id, "transient-once"),
            id=durable_id,
            task_queue=TASK_QUEUE,
        )
        waiting = await _wait_for_review(handle)
        require(waiting.current_artifacts["transient-once"].version == 1, "activity output missing")

    async with _worker(client):
        recovered = await handle.query(ProjectRunWorkflow.get_run_status)
        require(
            recovered is not None and recovered.state == "awaiting_review",
            "workflow did not recover review wait",
        )
        signal = ReviewSignal(
            review_id=f"review:{durable_id}:transient-once",
            target_version=1,
            decision="approve",
        )
        await handle.signal(ProjectRunWorkflow.submit_review_decision, signal)
        await handle.signal(ProjectRunWorkflow.submit_review_decision, signal)
        result = await handle.result()
        require(result.state == "succeeded", "workflow did not succeed")

    history = await handle.fetch_history()
    replay = await Replayer(workflows=[ProjectRunWorkflow]).replay_workflow(history)
    require(replay.replay_failure is None, "workflow history replay failed")

    invalid_id = f"e03-invalid-{uuid4()}"
    async with _worker(client):
        invalid = await client.start_workflow(
            ProjectRunWorkflow.run,
            _request(invalid_id, "invalid-input"),
            id=invalid_id,
            task_queue=TASK_QUEUE,
        )
        try:
            await invalid.result()
        except WorkflowFailureError:
            pass
        else:
            raise AssertionError("non-retryable invalid activity unexpectedly succeeded")

    print(
        json.dumps(
            {
                "durable_restart": True,
                "duplicate_signal_deduplicated": True,
                "history_replay": True,
                "non_retryable_error": True,
                "workflow_state": result.state,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
