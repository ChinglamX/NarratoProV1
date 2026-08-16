"""E06 bounded capacity probe: concurrent OCR + detection on frozen_test.

Simulates 2 concurrent projects running observation over the real
frozen_test corpus (12 episodes, series-isolated). Collects per-capability
latency (P50/P95), aggregate throughput (frames/sec) and peak process RSS.
This is engineering evidence for the capacity acceptance plan; target values
are pending project-owner approval and are NOT asserted here.

Reuses the benchmark sampling pipeline (shot detection -> bounded frames) and
the ProviderGateway research path exactly like build_e06_benchmark.py, but
runs two worker groups concurrently (worker A: OCR frames, worker B:
detection frames) on the same frozen corpus to observe resource contention.
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from packages.contracts.calibration import DatasetSplitManifest
from packages.providers import InvocationPolicy, ProviderGateway
from packages.providers.visual.paddle_detection import PaddleDetectionProvider
from packages.providers.visual.paddle_ocr import PaddleOCRProvider

CORPUS = Path("data/corpus")
FRAMES_ROOT = Path("evaluation/corpus/e06_visual/frames")
OUTPUT = Path("evaluation/reports/E06_CAPACITY_RESULTS.md")

_gateway = ProviderGateway()
_policy = InvocationPolicy(
    allow_research=True,
    allow_external_cloud=True,
    allowed_residency="CN",
    max_cost_micros=10_000_000,
    max_memory_bytes=4 * 1024**3,
    max_accelerator_memory_bytes=4 * 1024**3,
)
_PROVIDERS = {
    "ocr": PaddleOCRProvider(),
    "detection": PaddleDetectionProvider(),
}


def _sample_frames(video: Path, *, max_frames: int) -> list[Path]:
    import subprocess  # nosec B404

    from scenedetect import ContentDetector, SceneManager, open_video

    video_obj = open_video(str(video))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))
    manager.detect_scenes(video_obj, show_progress=False)
    scenes = manager.get_scene_list()
    shots = (
        [
            (scene[0].get_seconds(), scene[1].get_seconds() - scene[0].get_seconds())
            for scene in scenes
        ]
        if scenes
        else [(0.0, float(video_obj.duration.get_seconds()))]
    )
    frames: list[Path] = []
    step = max(1, len(shots) // max_frames)
    for index, (start, duration) in enumerate(shots):
        if index % step != 0 and len(frames) >= max_frames:
            continue
        if len(frames) >= max_frames:
            break
        mid = start + duration / 2
        out = FRAMES_ROOT / f"probe_{len(frames):04d}.jpg"
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


def _run_one(capability: str, frame: Path, run_id: str) -> tuple[int, int, int]:
    """Run one provider call; returns (duration_ms, texts_or_boxes, error_code)."""
    from uuid import uuid4

    from packages.contracts import ProviderInvocationRequest

    request = ProviderInvocationRequest(
        capability=capability,
        inputs=({"artifact_id": str(uuid4()), "version": 1, "artifact_type": "SourceMedia"},),
        config_ref={"artifact_id": str(uuid4()), "version": 1, "artifact_type": "ConfigArtifact"},
        resource_profile_ref={
            "artifact_id": str(uuid4()),
            "version": 1,
            "artifact_type": "ResourceProfile",
        },
        idempotency_key=f"e06-capacity:{capability}:{run_id}:{frame.name}",
        timeout_ms=300_000,
        parameters={"frame_path": str(frame)},
    )
    started = time.monotonic()
    try:
        raw = _gateway.invoke(_PROVIDERS[capability], request, _policy)
        data = json.loads(raw.payload)
        count = len(data.get("ocr", [])) if capability == "ocr" else len(data.get("detections", []))
        return int((time.monotonic() - started) * 1000), count, 0
    except Exception as error:
        return int((time.monotonic() - started) * 1000), 0, str(error)[:80]


def _percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * pct))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-frames-per-episode", type=int, default=6)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit-episodes", help="comma list of item ids to run a subset (dev)")
    args = parser.parse_args()

    manifest_path = Path("evaluation/corpus/e06_visual/manifest.json")
    raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = DatasetSplitManifest.model_validate(
        {key: raw_manifest[key] for key in ("manifest_id", "version", "items")}
    )
    frozen = [item for item in manifest.items if item.split == "frozen_test"]
    if args.limit_episodes:
        wanted = set(args.limit_episodes.split(","))
        frozen = [item for item in frozen if item.item_id in wanted]
    print(f"probe episodes: {len(frozen)}")

    # Sample frames once per episode (shared between both workers).
    tasks: list[tuple[str, Path]] = []
    run_id = f"probe-{int(time.time())}"
    for item in frozen:
        video = CORPUS / item.artifact_ref.replace("data/corpus/", "")
        frames = _sample_frames(video, max_frames=args.max_frames_per_episode)
        for frame in frames:
            tasks.append(("ocr", frame))
            tasks.append(("detection", frame))
    print(
        f"total provider calls: {len(tasks)} "
        f"({len(frozen)} episodes x {args.max_frames_per_episode} frames x 2 capabilities)"
    )

    # Pre-warm both providers sequentially: PaddleX refuses reinitialization, so
    # first-time model loading must complete single-threaded before the
    # concurrent measurement phase (documented E06 limitation).
    warm_frame = Path("evaluation/corpus/e06_visual/frames/probe_0000.jpg")
    if tasks and warm_frame.exists():
        for cap in ("ocr", "detection"):
            duration_ms, _, error = _run_one(cap, warm_frame, f"warm-{run_id}")
            print(f"warmup {cap}: {duration_ms}ms" + (f" error={error}" if error else ""))

    started = time.monotonic()
    latencies: dict[str, list[int]] = {"ocr": [], "detection": []}
    counts: dict[str, int] = {"ocr": 0, "detection": 0}
    errors: Counter = Counter()
    peak_rss_bytes = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_run_one, cap, frame, run_id) for cap, frame in tasks]
        for future in futures:
            duration_ms, count, error = future.result()
            cap = tasks[futures.index(future)][0]
            latencies[cap].append(duration_ms)
            counts[cap] += count
            if error:
                errors[cap] += 1
            # macOS ru_maxrss is reported in bytes; Linux in KB.
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == "darwin":
                peak_rss_bytes = max(peak_rss_bytes, rss)
            else:
                peak_rss_bytes = max(peak_rss_bytes, rss * 1024)
    elapsed = time.monotonic() - started

    total_calls = len(tasks)
    per_cap = {
        cap: {
            "calls": len(latencies[cap]),
            "p50_ms": _percentile(latencies[cap], 0.5),
            "p95_ms": _percentile(latencies[cap], 0.95),
            "total_items": counts[cap],
            "errors": errors[cap],
        }
        for cap in ("ocr", "detection")
    }
    summary = {
        "episodes": len(frozen),
        "frames": len(tasks) // 2,
        "calls": total_calls,
        "elapsed_s": round(elapsed, 2),
        "throughput_calls_per_s": round(total_calls / elapsed, 2),
        "throughput_frames_per_s": round((len(tasks) // 2) / elapsed, 2),
        "peak_rss_mb": round(peak_rss_bytes / 1024 / 1024, 1),
        "per_capability": per_cap,
        "note": "engineering evidence; acceptance targets pending owner approval",
    }
    print(json.dumps(summary, indent=1, ensure_ascii=False))

    lines = [
        "# E06 容量并发 probe(engineering evidence)",
        "",
        "Date: 2026-08-16",
        "Status: Engineering evidence — acceptance targets pending project-owner approval",
        "",
        "方法:frozen_test 12 集抽帧,OCR + detection 并发",
        f"- episodes: {summary['episodes']},frames: {summary['frames']},",
        f"  calls: {summary['calls']}",
        f"- elapsed: {summary['elapsed_s']}s,throughput: ",
        f"  {summary['throughput_calls_per_s']} calls/s",
        f"- peak RSS: {summary['peak_rss_mb']} MB (ru_maxrss peak)",
        "",
        "| capability | calls | P50 (ms) | P95 (ms) | total items | errors |",
        "|---|---|---|---|---|---|",
    ]
    for cap in ("ocr", "detection"):
        info = per_cap[cap]
        lines.append(
            f"| {cap} | {info['calls']} | {info['p50_ms']} | {info['p95_ms']} | "
            f"{info['total_items']} | {info['errors']} |"
        )
    lines += [
        "",
        "说明:单机本地 CPU,Paddle 模型常驻;结果受宿主调度影响,仅作工程基线,",
        "不构成容量验收结论.验收需 owner 批准目标值后按 `E06_CAPACITY_ACCEPTANCE_PLAN.md` 执行.",
        "",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"report written: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
