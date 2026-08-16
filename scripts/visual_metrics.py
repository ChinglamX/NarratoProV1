"""E06 visual metrics: compare human ground truth against provider predictions.

Reads the annotation pack (samples.json) once ground_truth is filled by a
human reviewer and computes:
- OCR: character error rate (CER) via Levenshtein on matched predictions.
- Detection: precision / recall with IoU >= 0.5 matching.
Outputs a Quality Profile threshold suggestion record.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

OUTPUT = Path("evaluation/corpus/e06_visual/annotation/samples.json")


def _cer(predicted: str, reference: str) -> float:
    """Character error rate via Levenshtein distance (normalized by ref length)."""
    if not reference:
        return 0.0 if not predicted else 1.0
    distance = _levenshtein(predicted, reference)
    return distance / len(reference)


def _levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        for j, char_b in enumerate(b, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b))
            )
        previous = current
    return previous[-1]


def _iou(left: dict[str, float], right: dict[str, float]) -> float:
    x1 = max(left["x_min"], right["x_min"])
    y1 = max(left["y_min"], right["y_min"])
    x2 = min(left["x_max"], right["x_max"])
    y2 = min(left["y_max"], right["y_max"])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    intersection = (x2 - x1) * (y2 - y1)
    left_area = (left["x_max"] - left["x_min"]) * (left["y_max"] - left["y_min"])
    right_area = (right["x_max"] - right["x_min"]) * (right["y_max"] - right["y_min"])
    return intersection / (left_area + right_area - intersection)


def _match_boxes(
    predicted: list[dict[str, object]], reference: list[dict[str, object]], threshold: float = 0.5
) -> tuple[int, int, int]:
    used = [False] * len(reference)
    true_positive = 0
    for prediction in predicted:
        best_index = -1
        best_iou = threshold
        for index, target in enumerate(reference):
            if used[index]:
                continue
            value = _iou(prediction["region"], target["region"])  # type: ignore[arg-type]
            if value > best_iou:
                best_iou = value
                best_index = index
        if best_index >= 0:
            used[best_index] = True
            true_positive += 1
    return true_positive, len(predicted), len(reference)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, default=OUTPUT)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    args = parser.parse_args()

    samples = json.loads(args.samples.read_text(encoding="utf-8"))
    reviewed = [s for s in samples if s.get("reviewed")]
    if not reviewed:
        print("no reviewed samples yet; fill ground_truth + reviewed=true first")
        return 1

    cer_values: list[float] = []
    matched_texts = 0
    tp = fp_total = fn_total = 0
    for sample in reviewed:
        gt_ocr = [t["text"] for t in sample["ground_truth"]["ocr"]]
        pred_ocr = [t["text"] for t in sample["ocr"]]
        # greedy text match by order
        for index, reference in enumerate(gt_ocr):
            if index < len(pred_ocr):
                cer_values.append(_cer(pred_ocr[index], reference))
                matched_texts += 1
        det_tp, det_pred, det_ref = _match_boxes(
            sample["detections"], sample["ground_truth"]["detections"], args.iou_threshold
        )
        tp += det_tp
        fp_total += det_pred - det_tp
        fn_total += det_ref - det_tp

    cer = sum(cer_values) / len(cer_values) if cer_values else None
    precision = tp / (tp + fp_total) if (tp + fp_total) else None
    recall = tp / (tp + fn_total) if (tp + fn_total) else None
    report = {
        "samples_reviewed": len(reviewed),
        "ocr": {"matched_texts": matched_texts, "cer": cer},
        "detection": {
            "iou_threshold": args.iou_threshold,
            "precision": precision,
            "recall": recall,
        },
        "threshold_suggestion": {
            "ocr_max_cer": 0.1 if cer is not None and cer <= 0.15 else None,
            "detection_min_recall": 0.8 if recall is not None and recall >= 0.7 else None,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
