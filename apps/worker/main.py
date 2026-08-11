"""Temporal worker bootstrap; workflows are registered incrementally by Epic."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from packages.foundation.settings import get_settings
from workflows.media import MediaIngestWorkflow, ingest_media_activity
from workflows.project import ProjectRunWorkflow, execute_conformance_activity
from workflows.timeline import TimelinePreviewWorkflow, render_preview_activity

CONTROL_TASK_QUEUE = "control"
WORKER_BUILD_ID = "narratopro-e03-v1"


async def serve() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_target,
        namespace=settings.temporal_namespace,
    )
    worker = Worker(
        client,
        task_queue=CONTROL_TASK_QUEUE,
        workflows=[ProjectRunWorkflow, TimelinePreviewWorkflow, MediaIngestWorkflow],
        activities=[execute_conformance_activity, render_preview_activity, ingest_media_activity],
        build_id=WORKER_BUILD_ID,
        use_worker_versioning=False,
    )
    await worker.run()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
