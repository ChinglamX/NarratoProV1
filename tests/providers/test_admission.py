"""Provider admission registry and fail-closed production gate tests."""

import pytest

from packages.contracts import ProviderAdmission, ProviderPackage
from packages.providers.admission import (
    CANDIDATE_VISUAL_PROVIDERS,
    ProviderAdmissionError,
    assert_production_ready,
    production_readiness_gaps,
)


def test_candidates_are_not_production() -> None:
    assert CANDIDATE_VISUAL_PROVIDERS
    for package in CANDIDATE_VISUAL_PROVIDERS:
        assert package.admission in {ProviderAdmission.RESEARCH, ProviderAdmission.BLOCKED}


def test_detection_candidate_is_open_source_not_agpl() -> None:
    detection = next(p for p in CANDIDATE_VISUAL_PROVIDERS if "detection" in p.capabilities)
    assert detection.identity.provider == "paddle-detection"
    assert detection.code_license == "Apache-2.0"
    # The AGPL ultralytics/yolo detector is explicitly excluded by project decision.
    assert all("ultralytics" not in p.identity.provider for p in CANDIDATE_VISUAL_PROVIDERS)


def test_production_admission_requires_complete_evidence() -> None:
    incomplete = next(p for p in CANDIDATE_VISUAL_PROVIDERS if p.model_checksum is None)
    gaps = production_readiness_gaps(incomplete)
    assert any("checksum" in gap for gap in gaps)
    assert any("commercial_use_allowed" in gap for gap in gaps)


def test_production_ready_package_passes_gate() -> None:
    base = CANDIDATE_VISUAL_PROVIDERS[0].model_dump(mode="json")
    base["admission"] = "production"
    base["model_checksum"] = "sha256:" + "a" * 64
    base["weight_license"] = "Apache-2.0"
    base["commercial_use_allowed"] = True
    base["identity"]["version"] = "4.0.0.1"
    package = ProviderPackage.model_validate(base)
    assert_production_ready(package)


def test_production_gate_fails_closed_on_missing_checksum() -> None:
    incomplete = next(p for p in CANDIDATE_VISUAL_PROVIDERS if p.model_checksum is None)
    package = incomplete.model_copy(update={"admission": ProviderAdmission.PRODUCTION})
    with pytest.raises(ProviderAdmissionError, match="model_checksum"):
        assert_production_ready(package)
