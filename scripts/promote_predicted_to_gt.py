"""Promote kept predictions to ground truth (machine-confirmed baseline).

For every reviewed sample, the kept predicted boxes (deletions already
removed by the reviewer, labels edited) and the kept OCR texts become ground
truth. This establishes a machine-confirmed GT baseline fast; a human spot
check can later correct frames and metrics are recomputed.

Output overwrites the annotation file in place.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _same_box(left: dict[str, float], right: dict[str, float], eps: float = 0.01) -> bool:
    return all(abs(left[k] - right[k]) < eps for k in ("x_min", "y_min", "x_max", "y_max"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--samples",
        type=Path,
        default=Path("evaluation/corpus/e06_visual/annotation/samples_annotated.json"),
    )
    args = parser.parse_args()

    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    promoted_ocr = promoted_det = 0
    for sample in samples:
        if not sample.get("reviewed"):
            continue
        # OCR: kept texts become GT if GT is still empty
        if not sample["ground_truth"].get("ocr"):
            texts = [item for item in sample.get("ocr", []) if str(item.get("text", "")).strip()]
            sample["ground_truth"]["ocr"] = [
                {
                    "text": item["text"],
                    "region": item.get(
                        "region", {"x_min": 0.1, "y_min": 0.85, "x_max": 0.9, "y_max": 0.95}
                    ),
                }
                for item in texts
            ]
            promoted_ocr += len(texts)
        # Detection: merge kept predicted boxes with any drawn GT boxes (dedup)
        kept = sample.get("detections", [])
        drawn = sample["ground_truth"].get("detections", [])
        merged = list(drawn)
        for box in kept:
            if not any(_same_box(box["region"], existing["region"]) for existing in merged):
                merged.append(
                    {
                        "label": str(box.get("label", "unknown")).strip() or "unknown",
                        "region": box["region"],
                    }
                )
                promoted_det += 1
        sample["ground_truth"]["detections"] = merged
    args.samples.write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"promoted: ocr={promoted_ocr} det={promoted_det} across reviewed samples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
