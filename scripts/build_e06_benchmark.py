"""Build the E06 visual benchmark from the registered real short-drama corpus.

Pipeline per episode: PySceneDetect shot segmentation -> sample one frame per
shot (bounded) -> PaddleOCR + RT-DETR on every sampled frame -> Volcengine Ark
VLM on a bounded subset -> aggregate per-capability metrics into
``evaluation/benchmarks/e06_visual_v1.json``.

The frozen_test split is measured but never used for tuning (DatasetSplit
contract). All providers run at ``research`` admission; this benchmark is the
evidence baseline for a future research->production review, not an admission.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path

from packages.contracts.calibration import DatasetSplitManifest
from packages.providers import InvocationPolicy, ProviderGateway
from packages.providers.visual.paddle_detection import PaddleDetectionProvider
from packages.providers.visual.paddle_ocr import PaddleOCRProvider
from packages.providers.visual.volcengine_ark_vlm import VolcengineArkVLMProvider

CORPUS = Path("data/corpus")
FRAMES_ROOT = Path("evaluation/corpus/e06_visual/frames")
OUTPUT = Path("evaluation/benchmarks/e06_visual_v1.json")

_gateway = ProviderGateway()
_policy = InvocationPolicy(
    allow_research=True,
    allow_external_cloud=True,
    allowed_residency="CN",
    max_cost_micros=10_000_000,
    max_memory_bytes=4 * 1024**3,
    max_accelerator_memory_bytes=4 * 1024**3,
)


def _request(capability: str, frame_path: Path, *, run_id: str) -> object:
    from uuid import uuid4

    from packages.contracts import ProviderInvocationRequest

    return ProviderInvocationRequest(
        capability=capability,
        inputs=({"artifact_id": str(uuid4()), "version": 1, "artifact_type": "SourceMedia"},),
        config_ref={"artifact_id": str(uuid4()), "version": 1, "artifact_type": "ConfigArtifact"},
        resource_profile_ref={
            "artifact_id": str(uuid4()),
            "version": 1,
            "artifact_type": "ResourceProfile",
        },
        idempotency_key=f"e06-bench:{capability}:{run_id}",
        timeout_ms=300_000,
        parameters={"frame_path": str(frame_path)},
    )


def _detect_shots(video: Path) -> list[tuple[float, float]]:
    """Return shot (start, duration) in seconds via PySceneDetect."""
    from scenedetect import ContentDetector, SceneManager, open_video

    video_obj = open_video(str(video))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))
    manager.detect_scenes(video_obj, show_progress=False)
    scenes = manager.get_scene_list()
    if scenes:
        return [
            (scene[0].get_seconds(), scene[1].get_seconds() - scene[0].get_seconds())
            for scene in scenes
        ]
    return [(0.0, float(video_obj.duration.get_seconds()))]


def _sample_frames(video: Path, shots: list[tuple[float, float]], *, max_frames: int) -> list[Path]:
    import subprocess  # nosec B404

    frames: list[Path] = []
    step = max(1, len(shots) // max_frames)
    for index, (start, duration) in enumerate(shots):
        if index % step != 0 and len(frames) >= max_frames:
            continue
        if len(frames) >= max_frames:
            break
        mid = start + duration / 2
        out = FRAMES_ROOT / f"shot_{len(frames):04d}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(  # nosec B603 B607
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{mid:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(out),
            ],
            check=False,
            timeout=30,
        )
        if out.exists() and out.stat().st_size > 0:
            frames.append(out)
    return frames


def _run_capability(capability: str, frames: list[Path], *, run_id: str) -> dict[str, object]:
    provider = {
        "ocr": PaddleOCRProvider(),
        "detection": PaddleDetectionProvider(),
        "vlm": VolcengineArkVLMProvider(),
    }[capability]
    results: list[dict[str, object]] = []
    durations: list[int] = []
    for frame in frames:
        try:
            raw = _gateway.invoke(provider, _request(capability, frame, run_id=run_id), _policy)  # type: ignore[arg-type]
            data = json.loads(raw.payload)
            durations.append(raw.duration_ms)
            results.append({"frame": frame.name, **data})
        except Exception as error:
            results.append({"frame": frame.name, "error": str(error)[:120]})
    counts = Counter()
    for item in results:
        if "error" in item:
            counts["errors"] += 1
        elif capability == "ocr":
            counts["texts"] += len(item.get("ocr", []))
        elif capability == "detection":
            counts["detections"] += len(item.get("detections", []))
        elif capability == "vlm":
            counts["claims"] += len(item.get("vlm_claims", []))
    return {
        "frames": len(frames),
        "results": results,
        "counts": dict(counts),
        "avg_duration_ms": round(sum(durations) / len(durations)) if durations else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-frames-per-episode", type=int, default=20)
    parser.add_argument("--vlm-frames-per-series", type=int, default=4)
    parser.add_argument("--limit-series", help="comma list to run a subset (dev)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest_path = Path("evaluation/corpus/e06_visual/manifest.json")
    raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = DatasetSplitManifest.model_validate(
        {key: raw_manifest[key] for key in ("manifest_id", "version", "items")}
    )
    series_by_split: dict[str, list[str]] = {}
    for item in manifest.items:
        series_by_split.setdefault(item.split, []).append(item.series_id)
    # dedupe while preserving order
    series_by_split = {
        split: list(dict.fromkeys(items)) for split, items in series_by_split.items()
    }

    if args.dry_run:
        print("series per split:", {s: len(v) for s, v in series_by_split.items()})
        return 0

    per_series: dict[str, dict[str, object]] = {}
    for split, series_ids in series_by_split.items():
        for series_id in series_ids:
            if args.limit_series and series_id not in args.limit_series.split(","):
                continue
            manifest_file = CORPUS / series_id / "manifest.json"
            meta = json.loads(manifest_file.read_text(encoding="utf-8"))
            episode_caps: dict[str, dict[str, object]] = {}
            for episode in meta["episodes"]:
                video = (CORPUS / series_id / episode["file"]).resolve()
                if not video.is_file():
                    continue
                started = time.perf_counter()
                shots = _detect_shots(video)
                frames = _sample_frames(video, shots, max_frames=args.max_frames_per_episode)
                caps: dict[str, dict[str, object]] = {}
                caps["ocr"] = _run_capability(
                    "ocr", frames, run_id=f"{series_id}:{episode['episode_id']}"
                )
                caps["detection"] = _run_capability(
                    "detection", frames, run_id=f"{series_id}:{episode['episode_id']}"
                )
                # VLM bounded to a subset of frames per series (API cost control)
                vlm_frames = frames[: args.vlm_frames_per_series]
                caps["vlm"] = _run_capability(
                    "vlm", vlm_frames, run_id=f"{series_id}:{episode['episode_id']}"
                )
                episode_caps[episode["episode_id"]] = {
                    "shots": len(shots),
                    "frames": len(frames),
                    "elapsed_s": round(time.perf_counter() - started, 1),
                    "capabilities": caps,
                }
                print(
                    f"  [{split}] {series_id} {episode['episode_id']}: {len(frames)} frames "
                    f"({round(time.perf_counter() - started, 1)}s)"
                )
            per_series[series_id] = {"split": split, "episodes": episode_caps}

    output = {
        "benchmark_version": "e06-visual-v1",
        "date": "2026-08-16",
        "provider_admission": {"ocr": "research", "detection": "research", "vlm": "research"},
        "series": per_series,
        "generated_by": "scripts/build_e06_benchmark.py",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"benchmark written: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
