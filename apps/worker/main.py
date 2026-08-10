"""Temporal worker bootstrap; workflows are registered incrementally by Epic."""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from packages.foundation.settings import get_settings


async def serve() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_target,
        namespace=settings.temporal_namespace,
    )
    worker = Worker(client, task_queue="control", workflows=[], activities=[])
    await worker.run()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
