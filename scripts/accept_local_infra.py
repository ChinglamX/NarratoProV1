#!/usr/bin/env python3
"""Run the repeatable A03 health, restart, and persistence acceptance drill."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404
import time
from collections.abc import Sequence
from pathlib import Path

SERVICES = (
    "postgres",
    "temporal",
    "temporal-ui",
    "minio",
    "otel-collector",
    "prometheus",
    "grafana",
)
IMAGE_PULL_ATTEMPTS = 5


def execute(command: Sequence[str]) -> None:
    subprocess.run(command, check=True)  # nosec B603


def capture(command: Sequence[str]) -> str:
    completed = subprocess.run(  # nosec B603
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def compose_command(root: Path, env_file: Path) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        str(root / "deploy/compose/docker-compose.yml"),
    ]


def pull_image(image: str) -> None:
    for attempt in range(1, IMAGE_PULL_ATTEMPTS + 1):
        try:
            execute(["docker", "pull", image])
            return
        except subprocess.CalledProcessError:
            if attempt == IMAGE_PULL_ATTEMPTS:
                raise
            delay_seconds = 2 ** (attempt - 1)
            print(
                f"Image pull failed for {image}; retrying "
                f"({attempt + 1}/{IMAGE_PULL_ATTEMPTS}) in {delay_seconds}s"
            )
            time.sleep(delay_seconds)


def accept(root: Path, env_file: Path) -> None:
    compose = compose_command(root, env_file)
    execute([*compose, "config", "--quiet"])
    images = tuple(
        dict.fromkeys(
            image for image in capture([*compose, "config", "--images"]).splitlines() if image
        )
    )
    if not images:
        raise RuntimeError("Compose config resolved no infrastructure images")
    for image in images:
        pull_image(image)
    execute([*compose, "up", "-d", "--wait", "--pull", "never"])
    execute(
        [
            *compose,
            "exec",
            "-T",
            "postgres",
            "sh",
            "-ceu",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -c "$1"',
            "--",
            "CREATE TABLE IF NOT EXISTS infra_acceptance "
            "(marker text PRIMARY KEY); INSERT INTO infra_acceptance VALUES "
            "('a03-persistence') ON CONFLICT DO NOTHING;",
        ]
    )
    execute(
        [
            *compose,
            "exec",
            "-T",
            "minio",
            "sh",
            "-ceu",
            "printf a03-persistence > /data/.narratopro-a03-probe",
        ]
    )
    execute([*compose, "restart", *SERVICES])
    execute([*compose, "up", "-d", "--wait", "--pull", "never"])
    execute(
        [
            *compose,
            "exec",
            "-T",
            "postgres",
            "sh",
            "-ceu",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "$1"',
            "--",
            "SELECT marker FROM infra_acceptance WHERE marker='a03-persistence';",
        ]
    )
    execute(
        [
            *compose,
            "exec",
            "-T",
            "minio",
            "sh",
            "-ceu",
            'test "$(cat /data/.narratopro-a03-probe)" = a03-persistence',
        ]
    )
    execute([*compose, "ps"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("deploy/compose/.env.example"),
        help="local-only Compose env file",
    )
    args = parser.parse_args()
    accept(args.root.resolve(), args.env_file.resolve())
    print("A03 local infrastructure acceptance: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
