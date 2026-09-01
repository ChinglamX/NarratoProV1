"""Enrich the E06 visual benchmark with semantic labels and E07 fusion proof.

1. OCR kind refinement (heuristic on region position/size):
   bottom band -> burned_in_subtitle, large area -> graphic_overlay, else scene_text.
2. Detection semantic labels via Volcengine Ark VLM: crops the detection boxes
   of a bounded frame subset, grids them into one image, asks the VLM for a
   per-cell label, and maps it back onto the detections.
3. E07 fusion proof: builds a VisualObservation from enriched OCR/detection data
   and runs ``fuse_observations`` to emit observable Facts (report only, no DB).

Writes an enriched copy: ``evaluation/benchmarks/e06_visual_v1_enriched.json``.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess  # nosec B404
import sys
import urllib.error
import urllib.request
from pathlib import Path

import cv2

from packages.contracts import ArtifactRef, ProviderIdentity
from packages.foundation.settings import get_settings
from packages.intelligence.facts import fuse_observations
from packages.intelligence.visual import normalize_visual_response

BENCHMARK = Path("evaluation/benchmarks/e06_visual_v1.json")
ENRICHED = Path("evaluation/benchmarks/e06_visual_v1_enriched.json")
CORPUS = Path("data/corpus")
FRAMES_ROOT = Path("evaluation/corpus/e06_visual/frames")

BOTTOM_BAND = 0.7  # y_min above this -> burned-in subtitle
GRAPHIC_MIN_AREA = 0.05  # fraction of frame area -> graphic overlay


def _classify_ocr_kind(region: dict[str, float]) -> str:
    area = (region["x_max"] - region["x_min"]) * (region["y_max"] - region["y_min"])
    if area >= GRAPHIC_MIN_AREA:
        return "graphic_overlay"
    if region["y_min"] >= BOTTOM_BAND:
        return "burned_in_subtitle"
    return "scene_text"


def _sample_frames(video: Path, max_frames: int) -> list[Path]:
    from scenedetect import ContentDetector, SceneManager, open_video

    video_obj = open_video(str(video))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=27.0))
    manager.detect_scenes(video_obj, show_progress=False)
    scenes = manager.get_scene_list()
    if not scenes:
        scenes = [(video_obj.get_fps(), video_obj.duration)]  # placeholder unused
        shots = [(0.0, float(video_obj.duration.get_seconds()))]
    else:
        shots = [(s[0].get_seconds(), s[1].get_seconds() - s[0].get_seconds()) for s in scenes]
    frames: list[Path] = []
    step = max(1, len(shots) // max_frames)
    for index, (start, duration) in enumerate(shots):
        if len(frames) >= max_frames:
            break
        if index % step != 0:
            continue
        mid = start + duration / 2
        out = FRAMES_ROOT / f"enrich_{len(frames):04d}.jpg"
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


def _ark_vlm_label_grid(image_path: Path, boxes: list[dict[str, object]]) -> list[str] | None:
    """Crop detection boxes into a grid, ask Ark VLM for per-cell labels."""
    settings = get_settings()
    api_key = settings.volcengine_ark_api_key
    model = settings.volcengine_ark_model
    if api_key is None or not model or not boxes:
        return None
    frame = cv2.imread(str(image_path))
    if frame is None:
        return None
    height, width = frame.shape[:2]
    crops = []
    for box in boxes:
        r = box["region"]
        x1 = int(r["x_min"] * width)
        y1 = int(r["y_min"] * height)
        x2 = max(x1 + 1, int(r["x_max"] * width))
        y2 = max(y1 + 1, int(r["y_max"] * height))
        crops.append(frame[y1:y2, x1:x2])
    # grid layout: one row per crop, scaled to a common height
    target_h = 160
    cells = []
    for crop in crops:
        scale = target_h / max(1, crop.shape[0])
        resized = cv2.resize(crop, (max(1, int(crop.shape[1] * scale)), target_h))
        cells.append(resized)
    grid = cv2.hconcat(cells)
    ok, encoded = cv2.imencode(".jpg", grid)
    if not ok:
        return None
    b64 = base64.b64encode(encoded.tobytes()).decode()
    prompt = (
        "The image is N cropped regions concatenated left-to-right. "
        "Give each region one short English label from: person, animal, "
        "subtitle, vehicle, weapon, food, building, prop, other. "
        'Output ONLY a JSON array like ["person","animal"], no other text.'
    )
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        }
    ).encode()
    request = urllib.request.Request(  # nosec B310
        settings.volcengine_ark_endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key.get_secret_value()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310
            parsed = json.loads(response.read())
        text = parsed["choices"][0]["message"]["content"]
        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            return None
        labels = json.loads(match.group(0))
        if not isinstance(labels, list) or len(labels) != len(boxes):
            return None
        return [str(label) for label in labels]
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
        return None


def _enrich_episode(
    series_id: str,
    episode_id: str,
    episode: dict[str, object],
    *,
    vlm_frames: int,
) -> dict[str, object]:
    manifest = json.loads((CORPUS / series_id / "manifest.json").read_text(encoding="utf-8"))
    entry = next((e for e in manifest["episodes"] if e["episode_id"] == episode_id), None)
    if entry is None:
        return {"error": "episode not in manifest"}
    video = (CORPUS / series_id / str(entry["file"])).resolve()
    if not video.is_file():
        return {"error": "video missing"}
    caps = episode["capabilities"]
    ocr_results = caps["ocr"]["results"]
    det_results = caps["detection"]["results"]
    enriched_ocr = 0
    enriched_det = 0
    vlm_calls = 0
    # 1) OCR kind refinement is pure computation on the persisted regions.
    for result in ocr_results:
        if "error" in result or "ocr" not in result:
            continue
        for item in result["ocr"]:
            if "region" in item and "kind" in item:
                item["kind"] = _classify_ocr_kind(item["region"])
                enriched_ocr += 1
    # 2) Detection semantic labels need frame pixels; sample a bounded subset.
    if vlm_frames > 0:
        frames = _sample_frames(video, max_frames=vlm_frames)
        for index, result in enumerate(det_results):
            if index >= len(frames) or "error" in result or "detections" not in result:
                continue
            if not result["detections"]:
                continue
            labels = _ark_vlm_label_grid(frames[index], result["detections"])
            vlm_calls += 1
            if labels:
                for detection, label in zip(result["detections"], labels, strict=False):
                    detection["label"] = label
                    enriched_det += 1
    return {
        "ocr_kind_refined": enriched_ocr,
        "det_labels_vlm": enriched_det,
        "vlm_calls": vlm_calls,
    }


def _fusion_proof(series_id: str, episode: dict[str, object]) -> dict[str, object]:
    """Build a VisualObservation from enriched data and emit observable Facts."""
    caps = episode["capabilities"]
    ocr_items = [
        item
        for r in caps["ocr"]["results"]
        if "ocr" in r
        for item in r["ocr"]
        if str(item.get("text", "")).strip() and item.get("region")
    ]
    det_items = [
        item
        for r in caps["detection"]["results"]
        if "detections" in r
        for item in r["detections"]
        if item.get("region")
    ]
    from uuid import uuid4

    raw = {
        "frames": [
            {
                "frame": {
                    "frame_ref": {
                        "artifact_id": str(uuid4()),
                        "version": 1,
                        "artifact_type": "SourceMedia",
                    },
                    "sample_id": str(uuid4()),
                    "source_time": {"value": 0, "rate_num": 25},
                },
                "ocr": [
                    {"text": i["text"], "region": i["region"], "kind": i.get("kind", "unknown")}
                    for i in ocr_items[:4]
                ],
                "detections": [
                    {"label": i.get("label", "unknown"), "region": i["region"]}
                    for i in det_items[:4]
                ],
            }
        ]
    }

    source_ref = ArtifactRef.model_validate(
        {
            "artifact_id": str(uuid4()),
            "version": 1,
            "artifact_type": "SourceMedia",
        }
    )
    visual_ref = ArtifactRef.model_validate(
        {
            "artifact_id": str(uuid4()),
            "version": 1,
            "artifact_type": "VisualObservation",
        }
    )
    fact_set_ref = ArtifactRef.model_validate(
        {
            "artifact_id": str(uuid4()),
            "version": 1,
            "artifact_type": "FactSet",
        }
    )
    provider = ProviderIdentity.model_validate(
        {
            "provider": "e06-benchmark",
            "version": "1",
            "implementation": "paddle+ark",
            "license": "Apache-2.0",
        }
    )
    observation = normalize_visual_response(
        raw,
        source_ref=source_ref,
        frame_plan_ref=visual_ref,
        raw_response_refs=(visual_ref,),
        provider=provider,
    )
    report = fuse_observations(
        fact_set_ref=fact_set_ref,
        visual_ref=visual_ref,
        visual=observation,
        id_factory=lambda: __import__("uuid").uuid4(),
    )
    return {
        "facts": len(report.fact_set.facts),
        "bundles": len(report.evidence_bundles),
        "incomplete": report.incomplete_partitions,
        "sample_fact_types": sorted({fact.fact_type.value for fact in report.fact_set.facts}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-frames-per-episode", type=int, default=20)
    parser.add_argument("--vlm-frames-per-episode", type=int, default=2)
    parser.add_argument("--limit-series", help="subset for dev")
    parser.add_argument("--skip-vlm", action="store_true")
    args = parser.parse_args()

    benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    stats = {
        "ocr_kind_refined": 0,
        "det_labels_vlm": 0,
        "vlm_calls": 0,
        "fusion_episodes": 0,
        "facts": 0,
    }
    for series_id, series in benchmark["series"].items():
        if args.limit_series and series_id not in args.limit_series.split(","):
            continue
        for ep_id, episode in series["episodes"].items():
            result = _enrich_episode(
                series_id,
                ep_id,
                episode,
                vlm_frames=0 if args.skip_vlm else args.vlm_frames_per_episode,
            )
            stats["ocr_kind_refined"] += result.get("ocr_kind_refined", 0)
            stats["det_labels_vlm"] += result.get("det_labels_vlm", 0)
            stats["vlm_calls"] += result.get("vlm_calls", 0)
            fusion = _fusion_proof(series_id, episode)
            stats["fusion_episodes"] += 1
            stats["facts"] += fusion.get("facts", 0)
            labels = result.get("det_labels_vlm", 0)
            print(
                f"  {series_id[:20]} {ep_id}: "
                f"ocr_kind={result.get('ocr_kind_refined', 0)}, "
                f"det_vlm_labels={labels}, facts={fusion.get('facts', 0)}"
            )
    ENRICHED.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"enriched -> {ENRICHED}")
    print("stats:", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
