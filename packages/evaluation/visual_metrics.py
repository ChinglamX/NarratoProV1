"""Deterministic capability-specific visual baseline metrics."""

from __future__ import annotations

from collections.abc import Sequence

from packages.contracts import BoundingBox, VLMClaim, VLMClaimKind
from packages.evaluation.speech_metrics import character_error_rate


def ocr_character_error_rate(reference: str, hypothesis: str) -> float:
    return character_error_rate(reference, hypothesis)


def box_iou(left: BoundingBox, right: BoundingBox) -> float:
    width = max(0.0, min(left.x_max, right.x_max) - max(left.x_min, right.x_min))
    height = max(0.0, min(left.y_max, right.y_max) - max(left.y_min, right.y_min))
    intersection = width * height
    left_area = (left.x_max - left.x_min) * (left.y_max - left.y_min)
    right_area = (right.x_max - right.x_min) * (right.y_max - right.y_min)
    return intersection / (left_area + right_area - intersection) if intersection else 0.0


def detection_precision_recall(
    reference: Sequence[BoundingBox],
    hypothesis: Sequence[BoundingBox],
    *,
    minimum_iou: float = 0.5,
) -> tuple[float, float]:
    unmatched = set(range(len(reference)))
    true_positive = 0
    for candidate in hypothesis:
        matches = [(index, box_iou(reference[index], candidate)) for index in unmatched]
        if matches:
            index, score = max(matches, key=lambda item: item[1])
            if score >= minimum_iou:
                true_positive += 1
                unmatched.remove(index)
    precision = true_positive / len(hypothesis) if hypothesis else float(not reference)
    recall = true_positive / len(reference) if reference else float(not hypothesis)
    return precision, recall


def tracking_id_switch_rate(assignments: Sequence[tuple[str, str]]) -> float:
    if not assignments:
        raise ValueError("tracking metric requires assignments")
    previous: dict[str, str] = {}
    switches = 0
    comparisons = 0
    for ground_truth, predicted in assignments:
        if ground_truth in previous:
            comparisons += 1
            switches += int(previous[ground_truth] != predicted)
        previous[ground_truth] = predicted
    return switches / comparisons if comparisons else 0.0


def vlm_evidence_compliance(claims: Sequence[VLMClaim]) -> float:
    if not claims:
        raise ValueError("VLM compliance requires claims")
    compliant = sum(
        claim.kind is not VLMClaimKind.VISIBLE or bool(claim.frame_evidence) for claim in claims
    )
    return compliant / len(claims)
