"""Canonical artifact-type registry shared by validation and schema generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArtifactTypeSpec:
    name: str
    domain: str
    owner: str


def _specs(domain: str, owner: str, names: str) -> tuple[ArtifactTypeSpec, ...]:
    return tuple(ArtifactTypeSpec(name=name, domain=domain, owner=owner) for name in names.split())


ARTIFACT_TYPE_SPECS = (
    *_specs(
        "Foundation",
        "control",
        "ConfigArtifact EffectiveConfigSnapshot ResourceProfile AutomationPolicy "
        "RightsGrant RightsManifest",
    ),
    *_specs(
        "Media",
        "intelligence",
        "SourceMedia MediaProbe ProxyMedia AudioStem EpisodeCatalog SceneShotCatalog "
        "FrameSamplePlan",
    ),
    *_specs(
        "Observation",
        "intelligence",
        "RawProviderResponse SpeechObservation VisualObservation OCRObservation Tracklet",
    ),
    *_specs("Identity", "intelligence", "IdentityGraph IdentityConflict"),
    *_specs("Fact", "intelligence", "FactSet EvidenceBundle SourceQualityFeatureSet"),
    *_specs("Story", "intelligence", "EventSet CharacterStateGraph CausalGraph StoryGraph"),
    *_specs(
        "Strategy",
        "strategy",
        "SellingPointSet StrategyCandidateSet HookCandidateSet CreativeBrief VariantPlan "
        "StrategyComparisonPackage",
    ),
    *_specs(
        "Timeline",
        "timeline",
        "NarrativeBeatGraph PatchProposal ConflictSet MasterTimeline OTIOExport PreviewManifest",
    ),
    *_specs(
        "Production",
        "production",
        "ClipCandidateSet CropPath RhythmPlan NarrationLineSet",
    ),
    *_specs("Voice", "production", "VoiceTakeSet VoiceAsset AlignmentArtifact"),
    *_specs("Audio", "production", "AudioAssetSelection MixPlan MixedAudio"),
    *_specs("Subtitle", "production", "SubtitleCueSet GraphicsCueSet ASSArtifact"),
    *_specs(
        "Render",
        "production",
        "RenderPlan ProxyRender FinalCandidate RenderExecutionReport",
    ),
    *_specs("Quality", "evaluation", "QualityEventSet TechnicalQCReport QualityReview"),
    *_specs(
        "Feedback",
        "evaluation",
        "CorrectionDataset DatasetManifest BenchmarkPredictionSet "
        "ProviderBenchmarkReport EvaluationRun",
    ),
    *_specs("Automation", "evaluation", "CalibrationArtifact DriftReport RoutingDecision"),
    *_specs("Release", "evaluation", "ReleaseReviewPackage ReleaseRecord PerformanceWindow"),
    *_specs("Experiment", "evaluation", "ExperimentPlan ExperimentResult ApplicableScope"),
)

ARTIFACT_TYPES = frozenset(spec.name for spec in ARTIFACT_TYPE_SPECS)


def validate_artifact_catalog() -> None:
    names = [spec.name for spec in ARTIFACT_TYPE_SPECS]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate artifact types: {', '.join(duplicates)}")


def require_known_artifact_type(value: str) -> str:
    if value not in ARTIFACT_TYPES:
        raise ValueError(f"unknown artifact_type: {value}")
    return value


validate_artifact_catalog()
