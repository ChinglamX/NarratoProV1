"""Visual provider normalization, Shot-local tracking, and bounded active sampling."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from packages.contracts import (
    ArtifactRef,
    BoundingBox,
    DetectionObservation,
    FrameEvidence,
    OCRObservation,
    ProviderIdentity,
    RationalTime,
    SupplementarySampleRequest,
    TextTrack,
    Tracklet,
    TrackPoint,
    VisualObservation,
)


def _confidence(score: float | None, scope: str) -> dict[str, object]:
    if score is None:
        return {
            "score": None,
            "status": "unavailable",
            "method": "provider-score-unavailable",
            "applicable_scope": scope,
            "risk_class": "high",
        }
    return {
        "score": min(1.0, max(0.0, score)),
        "status": "shadow",
        "method": "provider-score-uncalibrated",
        "applicable_scope": scope,
        "risk_class": "high",
    }


def _frame(value: dict[str, Any]) -> FrameEvidence:
    return FrameEvidence.model_validate(value)


def normalize_visual_response(
    raw: dict[str, Any],
    *,
    source_ref: ArtifactRef,
    frame_plan_ref: ArtifactRef,
    raw_response_refs: Sequence[ArtifactRef],
    provider: ProviderIdentity,
) -> VisualObservation:
    frames = raw.get("frames", [])
    if not isinstance(frames, list):
        raise ValueError("visual response frames must be an array")
    ocr: list[dict[str, object]] = []
    detections: list[dict[str, object]] = []
    faces: list[dict[str, object]] = []
    embeddings: list[dict[str, object]] = []
    claims: list[dict[str, object]] = []
    quality: list[dict[str, object]] = []
    for item in frames:
        if not isinstance(item, dict):
            raise ValueError("visual frame result must be an object")
        frame = _frame(item["frame"])
        for text in item.get("ocr", []):
            ocr.append(
                {
                    "observation_id": uuid4(),
                    "frame": frame,
                    "text": text["text"],
                    "region": text["region"],
                    "kind": text.get("kind", "unknown"),
                    "provider": provider,
                    "confidence": _confidence(text.get("score"), "visual-ocr:v1"),
                }
            )
        for detection in item.get("detections", []):
            detections.append(
                {
                    "observation_id": uuid4(),
                    "frame": frame,
                    "label": detection["label"],
                    "region": detection["region"],
                    "provider": provider,
                    "confidence": _confidence(detection.get("score"), "visual-detection:v1"),
                }
            )
        for face in item.get("faces", []):
            faces.append(
                {
                    "observation_id": uuid4(),
                    "frame": frame,
                    "region": face["region"],
                    "pose": face.get("pose"),
                    "quality_score": face["quality_score"],
                    "appearance_embedding_ref": face.get("appearance_embedding_ref"),
                    "provider": provider,
                    "confidence": _confidence(face.get("score"), "visual-face:v1"),
                }
            )
        for embedding in item.get("embeddings", []):
            vector = embedding["vector"]
            embeddings.append(
                {
                    "embedding_id": uuid4(),
                    "frame": frame,
                    "region": embedding.get("region"),
                    "vector": vector,
                    "dimensions": len(vector),
                    "normalized": embedding.get("normalized", False),
                    "provider": provider,
                }
            )
        for claim in item.get("vlm_claims", []):
            evidence = claim.get("frame_evidence", [frame.model_dump(mode="json")])
            claims.append(
                {
                    "claim_id": uuid4(),
                    "kind": claim["kind"],
                    "statement": claim["statement"],
                    "frame_evidence": evidence,
                    "confidence": _confidence(claim.get("score"), "visual-vlm:v1"),
                }
            )
        if "quality" in item:
            report = item["quality"]
            quality.append(
                {
                    "frame": frame,
                    "blur_score": report["blur_score"],
                    "mean_luminance": report["mean_luminance"],
                    "contrast": report["contrast"],
                    "usable_for_identity": report["usable_for_identity"],
                    "provider": provider,
                }
            )
    unavailable = tuple(raw.get("unavailable_capabilities", ()))
    has_model_output = any((ocr, detections, faces, embeddings, claims))
    status = "incomplete" if unavailable and (has_model_output or quality) else "complete"
    if unavailable and not has_model_output and not quality:
        status = "unavailable"
    return VisualObservation.model_validate(
        {
            "source_ref": source_ref,
            "frame_plan_ref": frame_plan_ref,
            "raw_response_refs": raw_response_refs,
            "ocr": ocr,
            "detections": detections,
            "faces": faces,
            "embeddings": embeddings,
            "vlm_claims": claims,
            "quality": quality,
            "status": status,
            "unavailable_capabilities": unavailable,
        }
    )


def _iou(left: BoundingBox, right: BoundingBox) -> float:
    width = max(0.0, min(left.x_max, right.x_max) - max(left.x_min, right.x_min))
    height = max(0.0, min(left.y_max, right.y_max) - max(left.y_min, right.y_min))
    intersection = width * height
    left_area = (left.x_max - left.x_min) * (left.y_max - left.y_min)
    right_area = (right.x_max - right.x_min) * (right.y_max - right.y_min)
    return intersection / (left_area + right_area - intersection) if intersection else 0.0


def build_text_tracks(
    observations: Sequence[OCRObservation], *, provider: ProviderIdentity
) -> tuple[TextTrack, ...]:
    """Group identical OCR without using ASR to rewrite the observed text."""

    groups: dict[tuple[str, object], list[OCRObservation]] = {}
    for observation in sorted(observations, key=lambda item: item.frame.source_time.seconds):
        groups.setdefault((observation.text, observation.kind), []).append(observation)
    return tuple(
        TextTrack.model_validate(
            {
                "track_id": uuid4(),
                "text": text,
                "kind": kind,
                "observations": items,
                "provider": provider,
                "confidence": _confidence(None, "visual-text-track:v1"),
            }
        )
        for (text, kind), items in groups.items()
    )


def build_shot_tracklets(
    detections: Sequence[DetectionObservation],
    *,
    shot_ref: ArtifactRef,
    provider: ProviderIdentity,
    minimum_iou: float = 0.3,
) -> tuple[Tracklet, ...]:
    """Deterministic Shot-local baseline; it never links across Shot refs."""

    ordered = sorted(detections, key=lambda item: item.frame.source_time.seconds)
    groups: list[list[DetectionObservation]] = []
    for detection in ordered:
        match = next(
            (
                group
                for group in groups
                if group[-1].label == detection.label
                and _iou(group[-1].region, detection.region) >= minimum_iou
            ),
            None,
        )
        if match is None:
            groups.append([detection])
        else:
            match.append(detection)
    return tuple(
        Tracklet.model_validate(
            {
                "tracklet_id": uuid4(),
                "shot_ref": shot_ref,
                "label": group[0].label,
                "points": [
                    TrackPoint(
                        detection_id=item.observation_id,
                        frame=item.frame,
                        region=item.region,
                    )
                    for item in group
                ],
                "detection_coverage": len(group) / len(ordered),
                "occlusion_ratio": 0.0,
                "representative_frame_ref": group[0].frame.frame_ref,
                "provider": provider,
                "confidence": _confidence(None, "shot-tracklet:v1"),
            }
        )
        for group in groups
    )


def request_supplementary_samples(
    *,
    source_ref: ArtifactRef,
    shot_ref: ArtifactRef,
    reason: str,
    requested_times: Sequence[RationalTime],
    remaining_budget: int,
) -> SupplementarySampleRequest:
    return SupplementarySampleRequest(
        request_id=uuid4(),
        source_ref=source_ref,
        shot_ref=shot_ref,
        reason=reason,
        expected_uncertainty_reduction=(
            "Collect additional source frames for unresolved observation"
        ),
        requested_times=tuple(requested_times),
        remaining_shot_budget=remaining_budget,
    )
