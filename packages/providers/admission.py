"""Semantic visual provider admission registry and production-readiness gate.

The G01 ProviderPackage contract already carries code/weight license,
commercial-use posture, model checksum and admission state. This module
centralises the *candidate* semantic visual providers (OCR / detection /
tracking / embedding / VLM) so their admission state lives in code, and
provides a fail-closed validator: a package may only be admitted as
``production`` when every production requirement is evidenced. This enforces
ADR-032 (no synthetic production approval) at the data boundary.
"""

from __future__ import annotations

from packages.contracts import ProviderAdmission, ProviderPackage

# Pinned model weight checksums (verified 2026-08-15 from the official Paddle
# model source downloads into .paddlex-cache).
_PP_OCRV6_MEDIUM_DET_SHA = "sha256:85218d2e3d98f5a21c58b4220627be923a97aee5db3cc71f39536ab31ac53960"
_PP_OCRV6_MEDIUM_REC_SHA = "sha256:1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319"
_RT_DETR_L_SHA = "sha256:51200fe6bb524263985c462d1a1ce5af48a3909136638e9d3ab13ed488ba19a8"

# Model/weight license facts below are stated as candidate values that MUST be
# re-verified against the exact pinned revision before any production upgrade;
# no package here is admitted as production.
CANDIDATE_VISUAL_PROVIDERS: tuple[ProviderPackage, ...] = (
    ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "paddleocr",
                "implementation": "pp-ocrv6",
                "version": "paddleocr-3.7.0-paddlex-3.7.2",
                "license": "Apache-2.0",
            },
            "capabilities": ["ocr"],
            "admission": "research",
            "code_license": "Apache-2.0",
            "weight_license": "Apache-2.0",
            "commercial_use_allowed": False,
            "model_checksum": _PP_OCRV6_MEDIUM_DET_SHA,
            "data_policy": {
                "execution_location": "local",
                "allowed_residencies": ["CN", "LOCAL"],
                "transmits_source_media": False,
                "retains_input": False,
            },
            "supported_hardware": ["cpu", "metal"],
            "deterministic": True,
            "retry_safe": True,
            "max_batch_size": 16,
            "known_limitations": [
                "models pinned: PP-OCRv6_medium_det (checksum above) + PP-OCRv6_medium_rec "
                f"({_PP_OCRV6_MEDIUM_REC_SHA}); verified 2026-08-15 on demo frame "
                "(1.46s CPU); real short-drama OCR benchmark and subtitle/text-box "
                "quality still pending",
            ],
        }
    ),
    ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "paddle-detection",
                "implementation": "rt-detr-l",
                "version": "paddlex-3.7.2",
                "license": "Apache-2.0",
            },
            "capabilities": ["detection"],
            "admission": "research",
            "code_license": "Apache-2.0",
            "weight_license": "Apache-2.0",
            "commercial_use_allowed": False,
            "model_checksum": _RT_DETR_L_SHA,
            "data_policy": {
                "execution_location": "local",
                "allowed_residencies": ["CN", "LOCAL"],
                "transmits_source_media": False,
                "retains_input": False,
            },
            "supported_hardware": ["cpu", "metal"],
            "deterministic": True,
            "retry_safe": True,
            "max_batch_size": 16,
            "known_limitations": [
                "model pinned: RT-DETR-L (checksum above); verified 2026-08-15 on demo "
                "frame (2 detections); supersedes ultralytics/yolo (AGPL, not adopted); "
                "real short-drama detection benchmark still pending",
            ],
        }
    ),
    ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "bytetrack",
                "implementation": "tracker",
                "version": "pending-pin",
                "license": "MIT-pending-verify",
            },
            "capabilities": ["tracking"],
            "admission": "research",
            "code_license": "MIT",
            "weight_license": None,
            "commercial_use_allowed": False,
            "model_checksum": None,
            "data_policy": {
                "execution_location": "local",
                "allowed_residencies": ["CN", "LOCAL"],
                "transmits_source_media": False,
                "retains_input": False,
            },
            "supported_hardware": ["cpu"],
            "deterministic": False,
            "retry_safe": True,
            "max_batch_size": 1,
            "known_limitations": [
                "tracking quality depends on the chosen detector; no real series benchmark",
            ],
        }
    ),
    ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "openclip",
                "implementation": "siglip-visual-embedding",
                "version": "pending-pin",
                "license": "MIT-Apache2-pending-verify",
            },
            "capabilities": ["visual_embedding"],
            "admission": "research",
            "code_license": "MIT",
            "weight_license": "Apache-2.0-pending-verify",
            "commercial_use_allowed": False,
            "model_checksum": None,
            "data_policy": {
                "execution_location": "local",
                "allowed_residencies": ["CN", "LOCAL"],
                "transmits_source_media": False,
                "retains_input": False,
            },
            "supported_hardware": ["cpu", "metal"],
            "deterministic": True,
            "retry_safe": True,
            "max_batch_size": 32,
            "known_limitations": [
                "embedding is recall-only and never identity (ADR-033); retrieval benchmark "
                "needs a real corpus",
            ],
        }
    ),
    ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "volcengine-ark",
                "implementation": "doubao-seed-2-0-mini",
                "version": "doubao-seed-2-0-mini-260428",
                "license": "volcengine-ark-tos",
            },
            "capabilities": ["vlm"],
            "admission": "research",
            "code_license": "volcengine-ark-tos",
            "weight_license": None,
            "commercial_use_allowed": False,
            "model_checksum": None,
            "data_policy": {
                "execution_location": "external_cloud",
                "allowed_residencies": ["CN"],
                "transmits_source_media": True,
                "retains_input": True,
                "retention_days": 30,
            },
            "supported_hardware": ["cloud"],
            "deterministic": False,
            "retry_safe": True,
            "max_batch_size": 4,
            "known_limitations": [
                "project decision 2026-08-15: VLM via Volcengine Ark, model "
                "doubao-seed-2-0-mini-260428, endpoint ep-m-20260716234644-hqltj; "
                "verified 2026-08-15 on demo frame (HTTP 200, 8.1s; accurate scene/",
                "person/animal/text description); cost caps and real short-drama VLM "
                "benchmark still pending",
                "claims constrained by the VLM claim contract; frames are transmitted to the API",
            ],
        }
    ),
)


def production_readiness_gaps(package: ProviderPackage) -> list[str]:
    """Return the evidence gaps that block a ``production`` admission.

    Fail-closed: an empty list means the package carries all required
    production evidence. Missing checksum, unresolved license or missing
    commercial approval are hard gaps.
    """
    gaps: list[str] = []
    if package.model_checksum is None:
        gaps.append("model_checksum is required for production admission")
    if package.weight_license is None:
        gaps.append("weight_license is required for production admission")
    if not package.commercial_use_allowed:
        gaps.append("commercial_use_allowed must be explicitly approved")
    if "pending" in package.code_license or "pending" in (package.weight_license or ""):
        gaps.append("license posture contains unresolved 'pending' marker")
    if package.identity.version.startswith("pending"):
        gaps.append("exact pinned revision is required (identity.version)")
    return gaps


def assert_production_ready(package: ProviderPackage) -> None:
    """Raise unless the package carries full production evidence."""
    if package.admission is not ProviderAdmission.PRODUCTION:
        return  # non-production packages are not gated by readiness here
    gaps = production_readiness_gaps(package)
    if gaps:
        raise ProviderAdmissionError("; ".join(gaps))


class ProviderAdmissionError(RuntimeError):
    pass
