import subprocess
from collections.abc import Sequence
from pathlib import Path

import yaml

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
    readiness_calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(  # type: ignore[attr-defined]
        accept_local_infra,
        "probe_http_readiness",
        lambda compose: readiness_calls.append(tuple(compose)),
    )
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
    assert len(readiness_calls) == 2


def test_acceptance_drill_rejects_empty_image_config(monkeypatch: object) -> None:
    monkeypatch.setattr(accept_local_infra, "execute", lambda command: None)  # type: ignore[attr-defined]
    monkeypatch.setattr(accept_local_infra, "capture", lambda command: "\n")  # type: ignore[attr-defined]

    try:
        accept_local_infra.accept(Path("/repo"), Path("/repo/local.env"))
    except RuntimeError as error:
        assert str(error) == "Compose config resolved no infrastructure images"
    else:
        raise AssertionError("empty image configuration must fail closed")


def test_acceptance_drill_can_require_cached_images(monkeypatch: object) -> None:
    commands: list[tuple[str, ...]] = []

    def record(command: Sequence[str]) -> None:
        commands.append(tuple(command))

    monkeypatch.setattr(accept_local_infra, "execute", record)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        accept_local_infra,
        "capture",
        lambda command: "postgres:16.4\nminio/minio:fixed\n",
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        accept_local_infra,
        "probe_http_readiness",
        lambda compose: None,
    )

    accept_local_infra.accept(
        Path("/repo"),
        Path("/repo/local.env"),
        pull=False,
    )

    rendered = [" ".join(command) for command in commands]
    assert "docker image inspect --format={{.Id}} postgres:16.4" in rendered
    assert "docker image inspect --format={{.Id}} minio/minio:fixed" in rendered
    assert not any(command.startswith("docker pull ") for command in rendered)
    assert any("up -d --wait --pull never" in command for command in rendered)


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


def test_prometheus_host_port_is_configurable() -> None:
    compose_path = Path("deploy/compose/docker-compose.yml")
    compose = yaml.safe_load(compose_path.read_text())

    assert compose["services"]["prometheus"]["ports"] == [
        "127.0.0.1:${PROMETHEUS_HOST_PORT:-19090}:9090"
    ]


def test_http_readiness_uses_published_ports(monkeypatch: object) -> None:
    requested: list[tuple[str, int, str]] = []

    class Response:
        status = 200

        def read(self) -> bytes:
            return b"ok"

    class Connection:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host
            self.port = port

        def request(self, method: str, path: str) -> None:
            requested.append((self.host, self.port, path))

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            pass

    monkeypatch.setattr(  # type: ignore[attr-defined]
        accept_local_infra,
        "capture",
        lambda command: f"127.0.0.1:{command[-1]}\n",
    )
    monkeypatch.setattr(accept_local_infra.http.client, "HTTPConnection", Connection)

    accept_local_infra.probe_http_readiness(["docker", "compose"])

    assert requested == [
        ("127.0.0.1", 8080, "/"),
        ("127.0.0.1", 8889, "/metrics"),
        ("127.0.0.1", 9090, "/-/ready"),
        ("127.0.0.1", 3000, "/api/health"),
    ]
