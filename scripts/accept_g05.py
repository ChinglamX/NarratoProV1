"""Bounded local G05 engineering load probe; it never grants production admission."""

from __future__ import annotations

import argparse
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from packages.contracts import ArtifactRef, ProviderInvocationRequest
from packages.evaluation.qualification import load_qualification, qualification_summary
from packages.providers.visual import OpenCVContourProvider


def _ref(kind: str) -> ArtifactRef:
    return ArtifactRef(artifact_id=uuid4(), version=1, artifact_type=kind)


def _invoke(path: Path, sequence: int) -> int:
    request = ProviderInvocationRequest.model_validate(
        {
            "capability": "detection",
            "inputs": [_ref("ProxyMedia")],
            "config_ref": _ref("EffectiveConfigSnapshot"),
            "resource_profile_ref": _ref("ResourceProfile"),
            "idempotency_key": f"g05-load-{sequence}",
            "timeout_ms": 30_000,
            "parameters": {"frame_path": str(path)},
        }
    )
    return OpenCVContourProvider().infer(request).duration_ms


def visual_concurrency_probe(path: Path, *, workers: int, requests: int) -> dict[str, object]:
    if workers <= 0 or requests <= 0:
        raise ValueError("workers and requests must be positive")
    path.resolve(strict=True)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        durations = list(executor.map(lambda index: _invoke(path, index), range(requests)))
    ordered = sorted(durations)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return {
        "provider_admission": "research",
        "workers": workers,
        "requests": requests,
        "successes": len(durations),
        "p50_ms": statistics.median(durations),
        "p95_ms": ordered[p95_index],
        "production_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=Path, default=Path("demo_frames/frame_0001.jpg"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--requests", type=int, default=16)
    args = parser.parse_args()
    result = {
        "qualification": qualification_summary(
            load_qualification(Path("evaluation/qualification/e06_g05.json"))
        ),
        "visual_concurrency": visual_concurrency_probe(
            args.frame, workers=args.workers, requests=args.requests
        ),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
