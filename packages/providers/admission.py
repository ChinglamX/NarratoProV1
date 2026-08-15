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

# Model/weight license facts below are stated as candidate values that MUST be
# re-verified against the exact pinned revision before any production upgrade;
# no package here is admitted as production.
CANDIDATE_VISUAL_PROVIDERS: tuple[ProviderPackage, ...] = (
    ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "paddleocr",
                "implementation": "pp-ocrv5",
                "version": "3.x-pending-pin",
                "license": "Apache-2.0-weight-pending-verify",
            },
            "capabilities": ["ocr"],
            "admission": "research",
            "code_license": "Apache-2.0",
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
            "max_batch_size": 16,
            "known_limitations": [
                "runtime/model not pinned; no checksum; no real short-drama OCR benchmark",
                "subtitle/text-box quality on drama captions unmeasured",
            ],
        }
    ),
    ProviderPackage.model_validate(
        {
            "identity": {
                "provider": "ultralytics",
                "implementation": "yolo-detector",
                "version": "pending-pin",
                "license": "AGPL-3.0-pending-decision",
            },
            "capabilities": ["detection"],
            "admission": "blocked",
            "code_license": "AGPL-3.0",
            "weight_license": "AGPL-3.0",
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
            "max_batch_size": 16,
            "known_limitations": [
                "AGPL posture undecided: production short-drama use requires Enterprise "
                "license or an Apache-2.0 alternative",
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
                "provider": "qwen-vl",
                "implementation": "local-vlm",
                "version": "pending-pin",
                "license": "Apache-2.0-pending-verify",
            },
            "capabilities": ["vlm"],
            "admission": "research",
            "code_license": "Apache-2.0",
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
            "deterministic": False,
            "retry_safe": True,
            "max_batch_size": 4,
            "known_limitations": [
                "local-vs-API deployment undecided; claims constrained by the VLM claim contract",
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
