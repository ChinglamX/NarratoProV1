"""Build the E06 human-annotation pack from the frozen_test split.

Samples frames from the frozen_test series, re-runs OCR + detection to
pre-fill predicted labels, and writes a review checklist where a human
verifies/corrects ground truth. Once GT is filled, scripts/visual_metrics.py
computes CER / detection precision-recall to produce Quality Profile
thresholds (the missing evidence for production admission).
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404
import sys
from pathlib import Path

from packages.contracts.calibration import DatasetSplitManifest
from packages.providers import InvocationPolicy, ProviderGateway
from packages.providers.visual.paddle_detection import PaddleDetectionProvider
from packages.providers.visual.paddle_ocr import PaddleOCRProvider

CORPUS = Path("data/corpus")
FRAMES = Path("evaluation/corpus/e06_visual/annotation/frames")
OUTPUT = Path("evaluation/corpus/e06_visual/annotation/samples.json")

_gateway = ProviderGateway()
_policy = InvocationPolicy(
    allow_research=True,
    allow_external_cloud=False,
    allowed_residency="CN",
    max_cost_micros=0,
    max_memory_bytes=4 * 1024**3,
    max_accelerator_memory_bytes=4 * 1024**3,
)


def _request(capability: str, frame: Path) -> object:
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
        idempotency_key=f"e06-annotation:{capability}:{frame.name}",
        timeout_ms=120_000,
        parameters={"frame_path": str(frame)},
    )


def _predict(capability: str, frame: Path) -> list[dict[str, object]]:
    provider = {
        "ocr": PaddleOCRProvider(),
        "detection": PaddleDetectionProvider(),
    }[capability]
    raw = _gateway.invoke(provider, _request(capability, frame), _policy)  # type: ignore[arg-type]
    data = json.loads(raw.payload)
    return data.get("ocr", data.get("detections", []))


def _sample_frame(video: Path, offset_seconds: float, index: int) -> Path:
    FRAMES.mkdir(parents=True, exist_ok=True)
    out = FRAMES / f"frozen_{index:03d}.jpg"
    subprocess.run(  # nosec B603 B607
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{offset_seconds:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(out),
        ],
        check=False,
        timeout=30,
    )
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"frame extraction failed: {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-per-series", type=int, default=8)
    args = parser.parse_args()

    manifest = DatasetSplitManifest.model_validate(
        {
            k: json.loads(
                Path("evaluation/corpus/e06_visual/manifest.json").read_text(encoding="utf-8")
            )[k]
            for k in ("manifest_id", "version", "items")
        }
    )
    frozen = sorted({item.series_id for item in manifest.items if item.split == "frozen_test"})
    samples: list[dict[str, object]] = []
    frame_index = 0
    for series_id in frozen:
        meta = json.loads((CORPUS / series_id / "manifest.json").read_text(encoding="utf-8"))
        for episode in meta["episodes"]:
            video = (CORPUS / series_id / str(episode["file"])).resolve()
            if not video.is_file() or video.stat().st_size < 1_000:
                continue
            duration = episode.get("duration_seconds") or 60.0
            count = min(args.frames_per_series, 4)
            for k in range(count):
                offset = min(duration - 0.5, (k + 1) * duration / (count + 1))
                frame = _sample_frame(video, offset, frame_index)
                ocr_pred = [
                    {"text": i["text"], "region": i["region"]} for i in _predict("ocr", frame)
                ]
                det_pred = [
                    {"label": i.get("label", "unknown"), "region": i["region"]}
                    for i in _predict("detection", frame)
                ]
                samples.append(
                    {
                        "sample_id": f"frozen_{frame_index:03d}",
                        "series_id": series_id,
                        "episode_id": episode["episode_id"],
                        "offset_seconds": round(offset, 2),
                        "frame": f"frames/{frame.name}",
                        "ocr": ocr_pred,
                        "detections": det_pred,
                        "ground_truth": {"ocr": [], "detections": []},  # human fills
                        "reviewed": False,
                        "reviewer": None,
                    }
                )
                print(
                    f"  {series_id} {episode['episode_id']} @{offset:.1f}s: "
                    f"ocr={len(ocr_pred)} det={len(det_pred)}"
                )
                frame_index += 1
            if frame_index >= args.frames_per_series * len(frozen):
                break
        if frame_index >= args.frames_per_series * len(frozen):
            break
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"annotation pack: {len(samples)} samples -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
