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


def _temporary_output_command(
    command: Sequence[str], *, output_path: Path, temporary: Path
) -> list[str]:
    """Replace the planned output with the atomic temporary destination."""
    rendered = list(command)
    if rendered and Path(rendered[-1]) == output_path:
        rendered[-1] = str(temporary)
    else:
        rendered.append(str(temporary))
    return rendered


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
    if not command or not Path(command[0]).name.startswith("ffmpeg"):
        raise RenderExecutionError("render command must invoke ffmpeg directly")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(
        f"{output_path.stem}.attempt-{attempt}.tmp{output_path.suffix}"
    )
    heartbeat({"stage": "render", "attempt": attempt})
    try:
        completed = subprocess.run(  # nosec B603
            _temporary_output_command(command, output_path=output_path, temporary=temporary),
            check=False,
            capture_output=True,
            timeout=3600,
        )
        if completed.returncode != 0 or not temporary.is_file():
            detail = completed.stderr.decode("utf-8", errors="replace")[-2_000:].strip()
            raise RenderExecutionError(
                f"ffmpeg render failed ({completed.returncode}): {detail or 'no stderr'}"
            )
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
