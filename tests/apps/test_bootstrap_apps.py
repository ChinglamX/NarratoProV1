import asyncio
import sys
from typing import Any

from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.cli.main import main as cli_main
from apps.worker import main as worker_main


def test_api_health_endpoints() -> None:
    client = TestClient(create_app())
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json()["environment"] == "development"


def test_cli_doctor_and_secret_safe_settings(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(sys, "argv", ["narratopro", "doctor"])
    cli_main()
    assert "healthy" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["narratopro", "settings"])
    cli_main()
    assert "secret_api_key_configured" in capsys.readouterr().out


def test_worker_registers_control_queue(monkeypatch: Any) -> None:
    observed: dict[str, Any] = {}

    async def connect(target: str, *, namespace: str) -> object:
        observed.update(target=target, namespace=namespace)
        return object()

    class Worker:
        def __init__(self, client: object, **kwargs: Any) -> None:
            observed.update(client=client, **kwargs)

        async def run(self) -> None:
            observed["ran"] = True

    monkeypatch.setattr(worker_main.Client, "connect", connect)
    monkeypatch.setattr(worker_main, "Worker", Worker)
    asyncio.run(worker_main.serve())
    assert observed["task_queue"] == "control"
    assert observed["ran"] is True
