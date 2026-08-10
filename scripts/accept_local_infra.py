#!/usr/bin/env python3
"""Run the repeatable A03 health, restart, and persistence acceptance drill."""

from __future__ import annotations

import argparse
import subprocess  # nosec B404
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


def execute(command: Sequence[str]) -> None:
    subprocess.run(command, check=True)  # nosec B603


def compose_command(root: Path, env_file: Path) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        str(root / "deploy/compose/docker-compose.yml"),
    ]


def accept(root: Path, env_file: Path) -> None:
    compose = compose_command(root, env_file)
    execute([*compose, "config", "--quiet"])
    execute([*compose, "up", "-d", "--wait"])
    execute(
        [
            *compose,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "narratopro",
            "-d",
            "narratopro",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
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
    execute([*compose, "up", "-d", "--wait"])
    execute(
        [
            *compose,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "narratopro",
            "-d",
            "narratopro",
            "-Atqc",
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
