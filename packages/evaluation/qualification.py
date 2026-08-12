"""Qualification matrix loading and deterministic summary."""

from __future__ import annotations

from pathlib import Path

from packages.contracts import ProductionQualification, QualificationStatus


def load_qualification(path: Path) -> ProductionQualification:
    return ProductionQualification.model_validate_json(path.read_text(encoding="utf-8"))


def qualification_summary(qualification: ProductionQualification) -> dict[str, object]:
    counts = {
        status.value: sum(check.status is status for check in qualification.checks)
        for status in QualificationStatus
    }
    blockers = [check.check_id for check in qualification.checks if check.blocker]
    return {
        "release_slice": qualification.release_slice,
        "checks": len(qualification.checks),
        "counts": counts,
        "blockers": blockers,
        "engineering_recommendation": qualification.engineering_recommendation.value,
        "decision": qualification.decision.value,
        "production_qualified": qualification.decision.value == "approved",
    }
