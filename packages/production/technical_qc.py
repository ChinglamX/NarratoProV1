"""Deterministic platform-profile technical and rights preflight checks."""

from __future__ import annotations

from datetime import datetime

from packages.contracts import ArtifactRef
from packages.contracts.render_release import (
    ReleaseRightsManifest,
    RightsManifestEntry,
    TechnicalCheck,
    TechnicalQCReport,
)
from packages.contracts.rights import RightsMetadata


def technical_qc(
    *,
    candidate_ref: ArtifactRef,
    profile_ref: ArtifactRef,
    measured: dict[str, int | float | str],
    required: dict[str, int | float | str],
) -> TechnicalQCReport:
    checks = []
    blockers: list[str] = []
    for key in sorted(required):
        passed = measured.get(key) == required[key]
        if not passed:
            blockers.append(f"technical:{key}")
        checks.append(
            TechnicalCheck(
                check_id=key,
                status="passed" if passed else "failed",
                measured={"actual": measured.get(key), "required": required[key]},
                profile_ref=profile_ref,
                blocker=True,
                detail=f"{key} {'matches' if passed else 'does not match'} platform profile",
            )
        )
    return TechnicalQCReport(
        candidate_ref=candidate_ref,
        checks=tuple(checks),
        blocker_codes=tuple(blockers),
        passed=not blockers,
    )


def rights_manifest(
    *,
    candidate_ref: ArtifactRef,
    platform: str,
    territory: str,
    evaluated_at: datetime,
    assets: tuple[tuple[ArtifactRef, str, RightsMetadata], ...],
) -> ReleaseRightsManifest:
    entries = []
    blockers: list[str] = []
    for asset_ref, role, rights_value in assets:
        release_blockers = rights_value.release_blockers(
            at=evaluated_at, platform=platform, territory=territory
        )
        blockers.extend(f"{role}:{item}" for item in release_blockers)
        entries.append(
            RightsManifestEntry(
                asset_ref=asset_ref,
                role=role,
                rights=rights_value,
                release_blockers=release_blockers,
            )
        )
    return ReleaseRightsManifest(
        candidate_ref=candidate_ref,
        platform=platform,
        territory=territory,
        evaluated_at=evaluated_at,
        entries=tuple(entries),
        blocker_codes=tuple(blockers),
    )
