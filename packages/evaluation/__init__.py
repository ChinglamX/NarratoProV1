"""Quality, calibration, automation and feedback domain."""

from packages.evaluation.benchmark import BenchmarkSummary, summarize_exact_match
from packages.evaluation.shadow import ShadowPrediction
from packages.evaluation.speech_metrics import (
    character_error_rate,
    diarization_error_rate,
    edit_distance,
    entity_character_error_rate,
    jaccard_error_rate,
    mean_boundary_deviation_ms,
)
from packages.evaluation.visual_metrics import (
    box_iou,
    detection_precision_recall,
    ocr_character_error_rate,
    tracking_id_switch_rate,
    vlm_evidence_compliance,
)

__all__ = [
    "BenchmarkSummary",
    "ShadowPrediction",
    "box_iou",
    "character_error_rate",
    "detection_precision_recall",
    "diarization_error_rate",
    "edit_distance",
    "entity_character_error_rate",
    "jaccard_error_rate",
    "mean_boundary_deviation_ms",
    "ocr_character_error_rate",
    "summarize_exact_match",
    "tracking_id_switch_rate",
    "vlm_evidence_compliance",
]
