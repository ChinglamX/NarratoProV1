"""Deterministic E11 render command construction from a RenderPlanContract."""

from __future__ import annotations

from pathlib import Path

from packages.contracts import RenderOperation, RenderPlanContract

FFMPEG = "ffmpeg"
TARGET_W = 720
TARGET_H = 1280


class RenderCommandError(RuntimeError):
    pass


def _us_param(op: RenderOperation, key: str) -> int:
    return int(op.parameters[key])  # type: ignore[arg-type]  # JsonValue numeric coercion


def _scale_filter() -> str:
    return (
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )


def build_render_command(
    *,
    plan: RenderPlanContract,
    source_paths: dict[str, Path],
    ass_path: Path | None,
    mixed_audio_path: Path | None,
    output_path: Path,
    ffmpeg_binary: str = FFMPEG,
) -> list[str]:
    """Build the ffmpeg argv for a proxy/final render.

    Video clips are trimmed at input (fast seek), scaled/padded, concatenated,
    subtitles burned with the ASS sidecar (requires libass ffmpeg), audio stems
    mixed, and everything muxed to H.264/AAC MP4.
    """
    if plan.blocker_codes:
        raise RenderCommandError("blocked RenderPlan cannot build a command")
    clips = [op for op in plan.operations if op.operation_type == "trim-clip"]
    audio_op = next((op for op in plan.operations if op.operation_type == "mix-audio"), None)
    ass_op = next((op for op in plan.operations if op.operation_type == "burn-ass"), None)
    if not clips:
        raise RenderCommandError("render plan has no video clips")

    command: list[str] = [ffmpeg_binary, "-y"]
    video_inputs: list[str] = []
    for index, op in enumerate(clips):
        source = source_paths.get(str(op.input_refs[0].artifact_id))
        if source is None or not source.is_file():
            raise RenderCommandError(f"source media unavailable: {op.input_refs[0].artifact_id}")
        command += ["-ss", f"{_us_param(op, 'source_start_us') / 1_000_000:.6f}"]
        command += ["-t", f"{_us_param(op, 'source_duration_us') / 1_000_000:.6f}"]
        command += ["-i", str(source)]
        video_inputs.append(
            f"[{index}:v]trim=0:{_us_param(op, 'source_duration_us') / 1_000_000:.6f},"
            f"{_scale_filter()},setpts=PTS-STARTPTS[v{index}]"
        )

    if audio_op is not None:
        if mixed_audio_path is None or not mixed_audio_path.is_file():
            raise RenderCommandError("MixedAudio path is unavailable")
        command += ["-i", str(mixed_audio_path)]

    concat_inputs = "".join(f"[v{i}]" for i in range(len(clips)))
    filter_complex: list[str] = [
        *video_inputs,
        f"{concat_inputs}concat=n={len(clips)}:v=1:a=0[vcat]",
    ]
    if ass_op is not None:
        if ass_path is None or not ass_path.is_file():
            raise RenderCommandError("ASS subtitle path is unavailable")
        filter_complex.append(f"[vcat]subtitles={ass_path}[vs]")
        video_output = "[vs]"
    else:
        video_output = "[vcat]"

    if audio_op is not None:
        audio_index = len(clips)
        filter_complex.append(
            f"[{audio_index}:a]atrim=0:{float(plan.expected_duration.seconds):.6f},"
            "asetpts=PTS-STARTPTS[aout]"
        )
        audio_output = "[aout]"
        command += ["-map", video_output, "-map", audio_output]
    else:
        command += ["-map", video_output]

    command += ["-filter_complex", ";".join(filter_complex)]
    command += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio_op is not None:
        command += ["-c:a", "aac"]
    command += ["-t", f"{float(plan.expected_duration.seconds):.6f}"]
    command += [str(output_path)]
    return command


def libass_available(ffmpeg_binary: str = FFMPEG) -> bool:
    """Detect whether the system ffmpeg supports the subtitles (libass) filter."""
    import subprocess  # nosec B404

    try:
        result = subprocess.run(  # nosec B603
            [ffmpeg_binary, "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return any(
            line.strip().startswith("..") and "subtitles" in line
            for line in result.stdout.splitlines()
        )
    except (subprocess.SubprocessError, OSError):
        return False
