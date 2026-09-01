"""Read-only media inventory for long-form test and production inputs."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess  # nosec B404 - fixed ffprobe argv; shell execution is never used
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VIDEO_SUFFIXES = frozenset({".mp4", ".mov", ".mkv", ".m4v", ".avi"})
POPULAR_MARKERS = ("热门", "热款", "hot", "popular")
EPISODE_PATTERN = re.compile(r"(?:第\s*)?(\d{1,4})(?:\s*集)?", re.IGNORECASE)


@dataclass(frozen=True)
class MediaFile:
    path: str
    relative_path: str
    size_bytes: int
    sha256: str
    episode_number: int | None
    is_popular_cut: bool
    duration_seconds: float | None
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None
    probe_warning: str | None = None


@dataclass(frozen=True)
class SeriesGroup:
    series_name: str
    episode_paths: tuple[str, ...]
    popular_cut_paths: tuple[str, ...]


@dataclass(frozen=True)
class MediaInventory:
    root: str
    rights_status: str
    files: tuple[MediaFile, ...]
    series: tuple[SeriesGroup, ...]
    warnings: tuple[str, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)


def build_media_inventory(root: Path) -> MediaInventory:
    """Inventory video inputs without changing or importing source media."""

    resolved = root.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"media root is not a readable directory: {resolved}")
    video_paths = sorted(
        path
        for path in resolved.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES
    )
    if not video_paths:
        raise ValueError(f"media root contains no supported video files: {resolved}")

    files = tuple(_inspect_file(path, resolved) for path in video_paths)
    grouped: dict[str, dict[str, list[str]]] = {}
    for item in files:
        series_name = _series_name(Path(item.relative_path))
        group = grouped.setdefault(series_name, {"episodes": [], "popular": []})
        target = "popular" if item.is_popular_cut else "episodes"
        group[target].append(item.path)
    series = tuple(
        SeriesGroup(
            series_name=name,
            episode_paths=tuple(values["episodes"]),
            popular_cut_paths=tuple(values["popular"]),
        )
        for name, values in sorted(grouped.items())
    )
    warnings = tuple(
        warning
        for warning in (
            "ffprobe unavailable; technical metadata is incomplete"
            if shutil.which("ffprobe") is None
            else None,
            "no popular-cut files were identified"
            if not any(item.is_popular_cut for item in files)
            else None,
        )
        if warning is not None
    )
    return MediaInventory(
        root=str(resolved),
        rights_status="user_declared_internal_use",
        files=files,
        series=series,
        warnings=warnings,
    )


def _inspect_file(path: Path, root: Path) -> MediaFile:
    probe, warning = _probe(path)
    streams = probe.get("streams", [])
    video: dict[str, Any] = next(
        (stream for stream in streams if stream.get("codec_type") == "video"), {}
    )
    audio: dict[str, Any] = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"), {}
    )
    duration = probe.get("format", {}).get("duration")
    relative = path.relative_to(root)
    return MediaFile(
        path=str(path),
        relative_path=str(relative),
        size_bytes=path.stat().st_size,
        sha256=_sha256(path),
        episode_number=_episode_number(path.stem),
        is_popular_cut=_is_popular(relative),
        duration_seconds=float(duration) if duration is not None else None,
        width=_optional_int(video.get("width")),
        height=_optional_int(video.get("height")),
        video_codec=_optional_str(video.get("codec_name")),
        audio_codec=_optional_str(audio.get("codec_name")),
        probe_warning=warning,
    )


def _probe(path: Path) -> tuple[dict[str, Any], str | None]:
    executable = shutil.which("ffprobe")
    if executable is None:
        return {}, "ffprobe unavailable"
    command = [
        executable,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(  # nosec B603
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return json.loads(completed.stdout), None
    except (subprocess.SubprocessError, json.JSONDecodeError) as error:
        return {}, f"ffprobe failed: {type(error).__name__}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _episode_number(stem: str) -> int | None:
    match = EPISODE_PATTERN.search(stem)
    return int(match.group(1)) if match else None


def _is_popular(relative: Path) -> bool:
    folded = str(relative).casefold()
    return any(marker.casefold() in folded for marker in POPULAR_MARKERS)


def _series_name(relative: Path) -> str:
    parts = [part for part in relative.parts[:-1] if not _is_popular(Path(part))]
    return parts[-1] if parts else relative.parent.name or "root"


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int | str) else None


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None
