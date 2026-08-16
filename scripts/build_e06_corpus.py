"""Register desktop short-drama media into the E06 visual benchmark corpus.

Scans the desktop 短剧素材 folder, matches hot-cut videos (男频热门) to their
original multi-episode series (又子剧场热款视频-男频), symlinks the media into
``data/corpus/<series_id>/episodes/`` and writes each series' ``manifest.json``
(rights + metadata). ffprobe fills duration/resolution back into the manifest.

All media is treated as legally processable per the project owner (2026-08-15).
Source media stays on the desktop; only symlinks + manifests live in the repo
corpus. This is a helper for human-in-the-loop benchmarking, not an automatic
production admission.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404
import sys
from pathlib import Path

BASE = Path.home() / "Desktop" / "短剧素材"
ORIGINALS = BASE / "又子剧场热款视频-男频"
HOTS = BASE / "男频热门"
CORPUS = Path("data/corpus")
MAX_ORIGINAL_EPISODES = 3  # bound benchmark scale; full series stay on desktop


def _series_id(title: str, index: int = 0) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", title).strip("-").lower()
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    slug = cleaned if len(cleaned) >= 3 else f"series-{index:02d}"
    return f"e06-{slug}"


def _normalize_title(name: str) -> str:
    return re.sub(r"^\d+\.\s*", "", name).strip()


def _index_of(title: str, titles: list[str]) -> int:
    return titles.index(title) if title in titles else 0


def _ffprobe_duration(path: Path) -> tuple[float | None, str | None]:
    try:
        result = subprocess.run(  # nosec B603 B607
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None, None
        info = json.loads(result.stdout)
        duration = info.get("format", {}).get("duration")
        video = next(
            (stream for stream in info.get("streams", []) if stream.get("codec_type") == "video"),
            {},
        )
        resolution = f"{video.get('width')}x{video.get('height')}" if video.get("width") else None
        return (float(duration) if duration else None), resolution
    except (subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return None, None


def _collect_originals() -> dict[str, dict[str, object]]:
    series: dict[str, dict[str, object]] = {}
    for directory in sorted(ORIGINALS.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue
        episodes = sorted(
            (p for p in directory.rglob("*.mp4") if p.is_file()),
            key=lambda p: _episode_sort_key(p.name),
        )
        if not episodes:
            continue
        title = _normalize_title(directory.name)
        series[title] = {
            "title": title,
            "episodes": episodes[:MAX_ORIGINAL_EPISODES],
            "all_episodes": episodes,
        }
    return series


def _episode_sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", name)
    return (int(match.group(1)) if match else 0, name)


def _collect_hot() -> dict[str, Path]:
    hot: dict[str, Path] = {}
    for file in HOTS.glob("*.mp4"):
        hot[_normalize_title(file.stem)] = file
    return hot


def _register_series(
    title: str,
    titles: list[str],
    originals: dict[str, dict[str, object]],
    hot: dict[str, Path],
) -> dict[str, object] | None:
    series_id = _series_id(title, index=_index_of(title, titles))
    target = CORPUS / series_id
    episodes: list[dict[str, object]] = []

    def add(name: str, source: Path) -> dict[str, object]:
        dest = target / "episodes" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.symlink_to(source)
        duration, resolution = _ffprobe_duration(source)
        return {
            "episode_id": Path(name).stem,
            "file": f"episodes/{name}",
            "duration_seconds": duration,
            "resolution": resolution,
        }

    original = originals.get(title)
    if original:
        for index, episode_path in enumerate(original["episodes"]):  # type: ignore[union-attr]
            episodes.append(add(f"e{index + 1:02d}.mp4", episode_path))
    if title in hot:
        episodes.append(add("hot.mp4", hot[title]))
    if not episodes:
        return None

    manifest = {
        "series_id": series_id,
        "title": title,
        "genre": "short-drama",
        "orientation": None,
        "episodes": episodes,
        "rights": {
            "rights_status": "approved",
            "allowed_purposes": ["evaluation"],
            "evidence_ref": "self-owned/authorized corpus per project owner 2026-08-15",
            "expires_at": None,
        },
        "admitted": True,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="scan/match only, no writes")
    args = parser.parse_args()

    originals = _collect_originals()
    hot = _collect_hot()
    titles = sorted(set(originals) | set(hot))
    registered: list[dict[str, object]] = []
    for title in titles:
        if args.dry_run:
            eps = len(originals[title]["episodes"]) if title in originals else 0  # type: ignore[index]
            print(f"  {title[:34]:<36} orig={eps} hot={'Y' if title in hot else '-'}")
            continue
        manifest = _register_series(title, titles, originals, hot)
        if manifest:
            registered.append(manifest)
    if args.dry_run:
        print(f"total series: {len(titles)}")
        return 0
    print(f"registered {len(registered)} series into {CORPUS}")
    for manifest in registered:
        print(f"  {manifest['series_id']:<36} {len(manifest['episodes'])} episodes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
