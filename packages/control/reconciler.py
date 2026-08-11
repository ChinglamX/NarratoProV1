"""Outbox reconciler port kept separate from database and Temporal adapters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SignalDelivery:
    event_id: str
    workflow_id: str
    payload: dict[str, Any]


async def deliver_signal(
    delivery: SignalDelivery,
    sender: Callable[[str, dict[str, Any]], Awaitable[None]],
) -> bool:
    await sender(delivery.workflow_id, delivery.payload)
    return True
