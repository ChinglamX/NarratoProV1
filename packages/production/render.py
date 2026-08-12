"""Atomic, bounded FFmpeg execution adapter for an approved RenderPlan command."""

from __future__ import annotations

import hashlib
import os
import subprocess  # nosec B404
from collections.abc import Callable, Sequence
from pathlib import Path

from packages.contracts import ArtifactRef
from packages.contracts.render_release import RenderExecutionReport, RenderPlanContract


class RenderExecutionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def execute_ffmpeg_plan(
    *,
    plan: RenderPlanContract,
    plan_ref: ArtifactRef,
    command: Sequence[str],
    output_path: Path,
    ffmpeg_version: str,
    attempt: int,
    heartbeat: Callable[[dict[str, object]], None],
) -> RenderExecutionReport:
    if plan.blocker_codes:
        raise RenderExecutionError("blocked RenderPlan cannot execute")
    if not command or Path(command[0]).name != "ffmpeg":
        raise RenderExecutionError("render command must invoke ffmpeg directly")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + f".attempt-{attempt}.tmp")
    heartbeat({"stage": "render", "attempt": attempt})
    try:
        completed = subprocess.run(  # nosec B603
            [*command, str(temporary)], check=False, capture_output=True, timeout=3600
        )
        if completed.returncode != 0 or not temporary.is_file():
            raise RenderExecutionError("ffmpeg render failed")
        checksum = sha256_file(temporary)
        os.replace(temporary, output_path)
        heartbeat({"stage": "render", "attempt": attempt, "complete": True})
        return RenderExecutionReport(
            render_plan_ref=plan_ref,
            attempt=attempt,
            output_blob_ref=str(output_path),
            output_checksum=checksum,
            duration_ms=0,
            peak_memory_bytes=0,
            ffmpeg_version=ffmpeg_version,
            succeeded=True,
        )
    finally:
        if temporary.exists():
            temporary.unlink()
