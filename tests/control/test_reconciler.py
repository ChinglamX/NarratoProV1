import asyncio

from packages.control.reconciler import SignalDelivery, deliver_signal


def test_reconciler_delivers_exact_payload() -> None:
    received: list[tuple[str, dict[str, object]]] = []

    async def sender(workflow_id: str, payload: dict[str, object]) -> None:
        received.append((workflow_id, payload))

    delivery = SignalDelivery("event", "workflow", {"decision": "approve"})
    assert asyncio.run(deliver_signal(delivery, sender))
    assert received == [("workflow", {"decision": "approve"})]
