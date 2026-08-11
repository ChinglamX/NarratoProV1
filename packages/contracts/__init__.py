"""Canonical public contracts; a concept must be defined here only once."""

from packages.contracts.calibration import (
    CalibrationPackManifest,
    DatasetSplitManifest,
    GuidelineManifest,
    SliceCatalogManifest,
    SliceDefinition,
)
from packages.contracts.evidence import (
    ConfidenceFactor,
    ConfidenceRecord,
    ConfidenceStatus,
    EvidenceLink,
    EvidenceType,
    FrameRange,
    RiskClass,
)
from packages.contracts.foundation import (
    UUID,
    ActorKind,
    ActorRef,
    ArtifactRef,
    Checksum,
    ProviderIdentity,
    RationalTime,
    TimeRange,
)
from packages.contracts.rights import (
    RightsGrantRef,
    RightsManifestRef,
    RightsMetadata,
    RightsStatus,
)

__all__ = [
    "UUID",
    "ActorKind",
    "ActorRef",
    "ArtifactRef",
    "CalibrationPackManifest",
    "Checksum",
    "ConfidenceFactor",
    "ConfidenceRecord",
    "ConfidenceStatus",
    "DatasetSplitManifest",
    "EvidenceLink",
    "EvidenceType",
    "FrameRange",
    "GuidelineManifest",
    "ProviderIdentity",
    "RationalTime",
    "RightsGrantRef",
    "RightsManifestRef",
    "RightsMetadata",
    "RightsStatus",
    "RiskClass",
    "SliceCatalogManifest",
    "SliceDefinition",
    "TimeRange",
]
