import subprocess
from collections.abc import Sequence
from pathlib import Path

from scripts import accept_local_infra


def test_acceptance_drill_covers_start_restart_and_persistence(monkeypatch: object) -> None:
    commands: list[tuple[str, ...]] = []

    def record(command: Sequence[str]) -> None:
        commands.append(tuple(command))

    def capture(command: Sequence[str]) -> str:
        commands.append(tuple(command))
        return "postgres:16.4\nminio/minio:fixed\npostgres:16.4\n"

    monkeypatch.setattr(accept_local_infra, "execute", record)  # type: ignore[attr-defined]
    monkeypatch.setattr(accept_local_infra, "capture", capture)  # type: ignore[attr-defined]
    accept_local_infra.accept(Path("/repo"), Path("/repo/local.env"))
    rendered = [" ".join(command) for command in commands]
    assert rendered[1].endswith("config --images")
    assert rendered[2:4] == [
        "docker pull postgres:16.4",
        "docker pull minio/minio:fixed",
    ]
    assert any("up -d --wait --pull never" in command for command in rendered)
    assert any("restart postgres temporal" in command for command in rendered)
    assert sum("a03-persistence" in command for command in rendered) == 4
    assert rendered[-1].endswith("ps")


def test_acceptance_drill_rejects_empty_image_config(monkeypatch: object) -> None:
    monkeypatch.setattr(accept_local_infra, "execute", lambda command: None)  # type: ignore[attr-defined]
    monkeypatch.setattr(accept_local_infra, "capture", lambda command: "\n")  # type: ignore[attr-defined]

    try:
        accept_local_infra.accept(Path("/repo"), Path("/repo/local.env"))
    except RuntimeError as error:
        assert str(error) == "Compose config resolved no infrastructure images"
    else:
        raise AssertionError("empty image configuration must fail closed")


def test_pull_image_retries_transient_failures(monkeypatch: object) -> None:
    attempts = 0
    delays: list[int] = []

    def flaky_execute(command: Sequence[str]) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(accept_local_infra, "execute", flaky_execute)  # type: ignore[attr-defined]
    monkeypatch.setattr(accept_local_infra.time, "sleep", delays.append)

    accept_local_infra.pull_image("example.invalid/fixed:1")

    assert attempts == 3
    assert delays == [1, 2]


def test_pull_image_stops_after_bounded_attempts(monkeypatch: object) -> None:
    attempts = 0
    delays: list[int] = []

    def failed_execute(command: Sequence[str]) -> None:
        nonlocal attempts
        attempts += 1
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(accept_local_infra, "execute", failed_execute)  # type: ignore[attr-defined]
    monkeypatch.setattr(accept_local_infra.time, "sleep", delays.append)

    try:
        accept_local_infra.pull_image("example.invalid/fixed:1")
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("exhausted image pull must preserve the final failure")

    assert attempts == accept_local_infra.IMAGE_PULL_ATTEMPTS
    assert delays == [1, 2, 4, 8]
