"""Versioned schema registry and deterministic cross-language generators."""

from __future__ import annotations

import json
import re
from itertools import pairwise
from pathlib import Path
from typing import Any, TypeAlias

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from packages.contracts.artifact_catalog import ARTIFACT_TYPE_SPECS, validate_artifact_catalog
from packages.contracts.artifacts import ArtifactDependency, ArtifactEnvelope, ProducerRecord
from packages.contracts.benchmark import (
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkPrediction,
    ProviderBenchmarkReport,
    SevereErrorDefinition,
    SliceMetric,
)
from packages.contracts.calibration import (
    CalibrationPackManifest,
    DatasetSplitManifest,
    GuidelineManifest,
    SliceCatalogManifest,
    SliceDefinition,
)
from packages.contracts.envelopes import (
    CommandEnvelope,
    ErrorDetail,
    ErrorEnvelope,
    EventEnvelope,
    PublicErrorDetail,
    PublicErrorEnvelope,
    ResourceErrorRef,
    TraceId,
)
from packages.contracts.evaluation import (
    ApplicableScope,
    CalibrationArtifact,
    Correction,
    DatasetManifest,
    EvaluationRun,
    QualityEvent,
    RoutingDecision,
)
from packages.contracts.evidence import (
    ConfidenceFactor,
    ConfidenceRecord,
    EvidenceLink,
    FrameRange,
)
from packages.contracts.facts import (
    EvidenceBundle,
    Fact,
    FactSet,
    FusionConflict,
    FusionReport,
    SourceQualityFeatureSet,
)
from packages.contracts.foundation import (
    ActorRef,
    ArtifactRef,
    Checksum,
    ProviderIdentity,
    RationalTime,
    TimeRange,
)
from packages.contracts.identity import (
    CharacterIdentity,
    IdentityConflict,
    IdentityCorrectionResult,
    IdentityEdge,
    IdentityGraph,
    IdentityNode,
    IdentityProposal,
    IdentityReviewPackage,
)
from packages.contracts.media import (
    EpisodeCatalog,
    FrameSamplePlan,
    MediaAsset,
    MediaTechnicalMetadata,
    SceneShotCatalog,
)
from packages.contracts.media_production import (
    AlignmentArtifact,
    ASSArtifact,
    AudioAssetSelection,
    ConformReport,
    MixedAudio,
    MixPlan,
    SubtitleCueSet,
    VoiceAsset,
    VoiceTakeSet,
)
from packages.contracts.media_production_qualification import (
    MediaProductionEngineeringQualification,
    MediaProductionSevereError,
)
from packages.contracts.providers import (
    ProviderDataPolicy,
    ProviderFailure,
    ProviderInvocationRequest,
    ProviderInvocationResult,
    ProviderPackage,
    ProviderResourceEstimate,
    RawProviderResponse,
)
from packages.contracts.qualification import ProductionQualification, QualificationCheck
from packages.contracts.render_release import (
    FinalCandidate,
    OfflineQualityReview,
    ReleaseRecord,
    ReleaseReviewPackage,
    ReleaseRightsManifest,
    RenderExecutionReport,
    RenderPlanContract,
    TechnicalQCReport,
)
from packages.contracts.render_release_qualification import (
    RenderReleaseEngineeringQualification,
    RenderReleaseSevereError,
)
from packages.contracts.rights import (
    RightsGrantRef,
    RightsManifestRef,
    RightsMetadata,
)
from packages.contracts.speech import (
    AlignedToken,
    SpeakerObservation,
    SpeechConflict,
    SpeechObservation,
    TranscriptSegment,
    VADSegment,
)
from packages.contracts.story import Character, Event, StoryArc, StoryEdge, StoryGraph
from packages.contracts.story_qualification import (
    StoryEngineeringQualification,
    StorySevereError,
)
from packages.contracts.story_reasoning import (
    ApprovedStorySnapshot,
    CausalGraph,
    CharacterState,
    CharacterStateGraph,
    EventCandidate,
    EventSet,
    StoryReasoningReport,
    StoryReviewPackage,
)
from packages.contracts.strategy import (
    CreativeBrief,
    HookCandidate,
    SellingPoint,
    SellingPointSet,
    StrategyCandidateSet,
    StrategyDirection,
)
from packages.contracts.strategy_candidates import (
    CandidateBlocker,
    CandidateBudget,
    CandidateValidation,
    HookCandidateSet,
    SellingPointCoverage,
)
from packages.contracts.strategy_config import (
    EffectiveStrategyConfig,
    GenreCandidate,
    GenreResolution,
    ResolvedStrategyValue,
    StrategyConfigConflict,
    StrategyProfile,
)
from packages.contracts.strategy_evaluation import (
    CandidateEvaluation,
    CostEstimate,
    CriticResult,
    DiversityPair,
    DiversityReport,
    FeasibilityReport,
    StrategyComparisonPackage,
    StrategyRisk,
)
from packages.contracts.strategy_qualification import (
    StrategyEngineeringQualification,
    StrategySevereError,
)
from packages.contracts.strategy_review import (
    ApprovedCreativeBrief,
    StrategyGateSelection,
    StrategyReviewPackage,
    VariantPlan,
    VariantSpec,
)
from packages.contracts.timeline import (
    MasterTimeline,
    TimelineConflict,
    TimelineItem,
    TimelinePatch,
    TimelineTrack,
)
from packages.contracts.timeline_intent import (
    AssemblyConflict,
    AudioIntent,
    BeatRhythm,
    ClipCandidate,
    ClipCandidateSet,
    ClipRetrievalQuery,
    ClipSelectionPlan,
    CompositionTarget,
    ContinuityReport,
    CropPath,
    DurationConflict,
    NarrationLineSet,
    NarrationPlanningReport,
    NarrativeBeatGraph,
    OverlayIntent,
    RhythmPlan,
    SourceSubtitleHandlingPlan,
    SubtitleIntent,
    TimelineAssemblyReport,
    TimelineIntentInput,
    TimelineIntentPackage,
    VisualPlanningReport,
)
from packages.contracts.timeline_qualification import (
    TimelineEngineeringQualification,
    TimelineSevereError,
)
from packages.contracts.visual import (
    BoundingBox,
    DetectionObservation,
    FaceObservation,
    FrameEvidence,
    OCRObservation,
    SupplementarySampleRequest,
    TextTrack,
    Tracklet,
    TrackPoint,
    VisualEmbedding,
    VisualObservation,
    VisualQualityReport,
    VLMClaim,
)

REGISTRY_VERSION = "2.16.0"
SCHEMA_ROOTS: tuple[type[BaseModel], ...] = (
    ASSArtifact,
    AssemblyConflict,
    ActorRef,
    ApprovedCreativeBrief,
    ApprovedStorySnapshot,
    AlignedToken,
    AlignmentArtifact,
    ApplicableScope,
    ArtifactDependency,
    ArtifactEnvelope,
    ArtifactRef,
    AudioAssetSelection,
    AudioIntent,
    BenchmarkCase,
    BenchmarkDataset,
    BenchmarkPrediction,
    BeatRhythm,
    BoundingBox,
    CalibrationArtifact,
    CalibrationPackManifest,
    CandidateBlocker,
    CandidateBudget,
    CandidateValidation,
    CandidateEvaluation,
    CausalGraph,
    CharacterIdentity,
    CharacterState,
    CharacterStateGraph,
    ClipCandidate,
    ClipCandidateSet,
    ClipRetrievalQuery,
    ClipSelectionPlan,
    CompositionTarget,
    Checksum,
    CommandEnvelope,
    ConfidenceFactor,
    ConfidenceRecord,
    ConformReport,
    ContinuityReport,
    Correction,
    CostEstimate,
    CreativeBrief,
    CriticResult,
    CropPath,
    DurationConflict,
    DatasetManifest,
    DatasetSplitManifest,
    DetectionObservation,
    DiversityPair,
    DiversityReport,
    ErrorDetail,
    ErrorEnvelope,
    EffectiveStrategyConfig,
    EpisodeCatalog,
    EventEnvelope,
    Event,
    EventCandidate,
    EventSet,
    EvaluationRun,
    EvidenceBundle,
    EvidenceLink,
    FrameRange,
    FrameSamplePlan,
    Fact,
    FactSet,
    FinalCandidate,
    FeasibilityReport,
    FusionConflict,
    FusionReport,
    FaceObservation,
    FrameEvidence,
    GuidelineManifest,
    GenreCandidate,
    GenreResolution,
    HookCandidate,
    HookCandidateSet,
    IdentityConflict,
    IdentityCorrectionResult,
    IdentityEdge,
    IdentityGraph,
    IdentityNode,
    IdentityProposal,
    IdentityReviewPackage,
    MasterTimeline,
    MediaAsset,
    MediaTechnicalMetadata,
    MediaProductionEngineeringQualification,
    MediaProductionSevereError,
    MixPlan,
    MixedAudio,
    OCRObservation,
    OfflineQualityReview,
    OverlayIntent,
    NarrativeBeatGraph,
    NarrationLineSet,
    NarrationPlanningReport,
    ProviderIdentity,
    ProviderBenchmarkReport,
    ProviderDataPolicy,
    ProviderFailure,
    ProviderInvocationRequest,
    ProviderInvocationResult,
    ProviderPackage,
    ProviderResourceEstimate,
    PublicErrorDetail,
    PublicErrorEnvelope,
    ProducerRecord,
    ProductionQualification,
    QualityEvent,
    QualificationCheck,
    RationalTime,
    RawProviderResponse,
    ResourceErrorRef,
    ReleaseRecord,
    ReleaseReviewPackage,
    ReleaseRightsManifest,
    RenderExecutionReport,
    RenderPlanContract,
    RenderReleaseEngineeringQualification,
    RenderReleaseSevereError,
    ResolvedStrategyValue,
    RightsGrantRef,
    RightsManifestRef,
    RightsMetadata,
    RoutingDecision,
    RhythmPlan,
    SceneShotCatalog,
    SevereErrorDefinition,
    SellingPoint,
    SellingPointSet,
    SellingPointCoverage,
    SpeakerObservation,
    SpeechConflict,
    SpeechObservation,
    SliceCatalogManifest,
    SliceDefinition,
    SliceMetric,
    SourceQualityFeatureSet,
    SourceSubtitleHandlingPlan,
    StoryArc,
    StoryEdge,
    StoryEngineeringQualification,
    StoryGraph,
    StoryReasoningReport,
    StoryReviewPackage,
    StorySevereError,
    SubtitleCueSet,
    SubtitleIntent,
    SupplementarySampleRequest,
    TextTrack,
    StrategyCandidateSet,
    StrategyComparisonPackage,
    StrategyConfigConflict,
    StrategyDirection,
    StrategyEngineeringQualification,
    StrategyProfile,
    StrategyRisk,
    StrategySevereError,
    StrategyGateSelection,
    StrategyReviewPackage,
    VariantPlan,
    VariantSpec,
    Character,
    TimelineConflict,
    TimelineEngineeringQualification,
    TimelineIntentInput,
    TimelineIntentPackage,
    TimelineAssemblyReport,
    TimelineSevereError,
    TechnicalQCReport,
    TimelineItem,
    TimelinePatch,
    TimelineTrack,
    Tracklet,
    TrackPoint,
    TranscriptSegment,
    TimeRange,
    TraceId,
    VADSegment,
    VoiceAsset,
    VoiceTakeSet,
    VisualEmbedding,
    VisualObservation,
    VisualQualityReport,
    VisualPlanningReport,
    VLMClaim,
)
JsonDict: TypeAlias = dict[str, Any]


def _definitions(ref_template: str) -> JsonDict:
    _, schema = models_json_schema(
        [(model, "validation") for model in SCHEMA_ROOTS],
        by_alias=True,
        ref_template=ref_template,
    )
    definitions = schema.get("$defs", {})
    if not isinstance(definitions, dict):
        raise ValueError("Pydantic schema definitions must be an object")
    titles = [item.get("title") for item in definitions.values() if isinstance(item, dict)]
    duplicate_titles = sorted({title for title in titles if title and titles.count(title) > 1})
    if duplicate_titles:
        raise ValueError(f"duplicate schema titles: {', '.join(duplicate_titles)}")
    return dict(sorted(definitions.items()))


def json_schema_document() -> JsonDict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://schemas.narratopro.local/contracts/{REGISTRY_VERSION}",
        "title": "NarratoPro Contract Registry",
        "x-registry-version": REGISTRY_VERSION,
        "$defs": _definitions("#/$defs/{model}"),
    }


def openapi_document() -> JsonDict:
    return {
        "openapi": "3.1.0",
        "info": {"title": "NarratoPro Contract Components", "version": REGISTRY_VERSION},
        "paths": {},
        "components": {"schemas": _definitions("#/components/schemas/{model}")},
    }


def artifact_registry_document() -> JsonDict:
    validate_artifact_catalog()
    return {
        "registry_version": REGISTRY_VERSION,
        "artifact_types": [
            {"name": spec.name, "domain": spec.domain, "owner": spec.owner}
            for spec in sorted(ARTIFACT_TYPE_SPECS, key=lambda item: item.name)
        ],
    }


def _literal(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _property_name(value: str) -> str:
    return value if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", value) else _literal(value)


def _typescript_type(schema: JsonDict) -> str:
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "const" in schema:
        return _literal(schema["const"])
    if "enum" in schema:
        return " | ".join(_literal(value) for value in schema["enum"])
    for keyword, separator in (("anyOf", " | "), ("oneOf", " | "), ("allOf", " & ")):
        if keyword in schema:
            return separator.join(f"({_typescript_type(item)})" for item in schema[keyword])
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(_typescript_type({**schema, "type": item}) for item in schema_type)
    if schema_type == "null":
        return "null"
    if schema_type == "boolean":
        return "boolean"
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "string":
        return "string"
    if schema_type == "array":
        if "prefixItems" in schema:
            return (
                "readonly ["
                + ", ".join(_typescript_type(item) for item in schema["prefixItems"])
                + "]"
            )
        return f"ReadonlyArray<{_typescript_type(schema.get('items', {}))}>"
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        members = [
            f"readonly {_property_name(name)}{'?' if name not in required else ''}: "
            f"{_typescript_type(value)};"
            for name, value in properties.items()
        ]
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            members.append(f"readonly [key: string]: {_typescript_type(additional)};")
        elif additional is True:
            members.append("readonly [key: string]: unknown;")
        return "{ " + " ".join(members) + " }"
    return "unknown"


def typescript_document() -> str:
    definitions = openapi_document()["components"]["schemas"]
    lines = [
        "// Generated by scripts/generate_contracts.py. DO NOT EDIT.",
        f"export const CONTRACT_REGISTRY_VERSION = {_literal(REGISTRY_VERSION)} as const;",
        "",
    ]
    for name, schema in definitions.items():
        generated_type = _typescript_type(schema)
        if name == "JsonValue" and not schema:
            generated_type = (
                "null | boolean | number | string | readonly JsonValue[] | "
                "{ readonly [key: string]: JsonValue }"
            )
        lines.append(f"export type {name} = {generated_type};")
    lines.extend(
        [
            "",
            "export interface ContractSchemas {",
            *[f"  readonly {name}: {name};" for name in definitions],
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def generated_outputs(root: Path) -> dict[Path, str]:
    version_dir = root / "generated" / "contracts" / "versions" / REGISTRY_VERSION

    def dump(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    return {
        version_dir / "json-schema.json": dump(json_schema_document()),
        version_dir / "openapi.json": dump(openapi_document()),
        version_dir / "artifact-types.json": dump(artifact_registry_document()),
        root / "generated" / "contracts" / "latest.json": dump(
            {"registry_version": REGISTRY_VERSION}
        ),
        root / "apps" / "review_web" / "src" / "generated" / "contracts.generated.ts": (
            typescript_document()
        ),
    }


def breaking_changes(previous: JsonDict, current: JsonDict) -> list[str]:
    """Detect the supported class of input-schema breaking changes."""

    errors: list[str] = []
    previous_defs = previous.get("$defs", {})
    current_defs = current.get("$defs", {})
    for name, old_schema in previous_defs.items():
        new_schema = current_defs.get(name)
        if new_schema is None:
            errors.append(f"removed schema: {name}")
            continue
        errors.extend(_schema_breaking_changes(old_schema, new_schema, name))
    return errors


def _schema_breaking_changes(old: JsonDict, new: JsonDict, path: str) -> list[str]:
    errors: list[str] = []
    if old == new:
        return errors
    if "$ref" in old and old.get("$ref") != new.get("$ref"):
        return [f"changed reference: {path}"]
    if "const" in old and old.get("const") != new.get("const"):
        return [f"changed constant: {path}"]
    if "enum" in old:
        removed = set(old["enum"]) - set(new.get("enum", []))
        errors.extend(f"removed enum value: {path}.{value}" for value in sorted(removed, key=str))
        return errors
    for union_keyword in ("anyOf", "oneOf"):
        if union_keyword in old:
            old_variants = {_canonical(item) for item in old[union_keyword]}
            new_variants = {_canonical(item) for item in new.get(union_keyword, [])}
            if not old_variants.issubset(new_variants):
                errors.append(f"narrowed {union_keyword}: {path}")
            return errors
    if old.get("type") != new.get("type"):
        errors.append(f"changed type: {path}")
        return errors
    if old.get("type") == "object" or "properties" in old:
        old_required = set(old.get("required", []))
        new_required = set(new.get("required", []))
        errors.extend(
            f"new required field: {path}.{field}" for field in sorted(new_required - old_required)
        )
        old_properties = old.get("properties", {})
        new_properties = new.get("properties", {})
        for field, old_field_schema in old_properties.items():
            if field not in new_properties:
                errors.append(f"removed field: {path}.{field}")
            else:
                errors.extend(
                    _schema_breaking_changes(
                        old_field_schema, new_properties[field], f"{path}.{field}"
                    )
                )
        if (
            old.get("additionalProperties", True) is not False
            and new.get("additionalProperties", True) is False
        ):
            errors.append(f"forbade additional properties: {path}")
        return errors
    if old.get("type") == "array":
        return _schema_breaking_changes(old.get("items", {}), new.get("items", {}), f"{path}[]")
    for keyword in ("minimum", "exclusiveMinimum", "minLength", "minItems"):
        if keyword in new and (keyword not in old or new[keyword] > old[keyword]):
            errors.append(f"tightened {keyword}: {path}")
    for keyword in ("maximum", "exclusiveMaximum", "maxLength", "maxItems"):
        if keyword in new and (keyword not in old or new[keyword] < old[keyword]):
            errors.append(f"tightened {keyword}: {path}")
    if "pattern" in new and old.get("pattern") != new["pattern"]:
        errors.append(f"changed pattern: {path}")
    return errors


def artifact_registry_breaking_changes(previous: JsonDict, current: JsonDict) -> list[str]:
    old_specs = {item["name"]: item for item in previous.get("artifact_types", [])}
    new_specs = {item["name"]: item for item in current.get("artifact_types", [])}
    errors: list[str] = []
    for name, old_spec in old_specs.items():
        if name not in new_specs:
            errors.append(f"removed artifact type: {name}")
        elif old_spec != new_specs[name]:
            errors.append(f"changed artifact owner/domain: {name}")
    return errors


def registry_history_errors(root: Path) -> list[str]:
    versions_root = root / "generated" / "contracts" / "versions"
    versions: list[tuple[tuple[int, int, int], Path]] = []
    for directory in versions_root.iterdir() if versions_root.exists() else ():
        if not directory.is_dir() or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", directory.name):
            continue
        major, minor, patch = (int(part) for part in directory.name.split("."))
        versions.append(((major, minor, patch), directory))
    versions.sort()
    errors: list[str] = []
    current_major, current_minor, current_patch = (
        int(part) for part in REGISTRY_VERSION.split(".")
    )
    current_tuple = (current_major, current_minor, current_patch)
    if versions and versions[-1][0] != current_tuple:
        errors.append("REGISTRY_VERSION must identify the newest generated version")
    for (previous_version, previous_dir), (current_version, current_dir) in pairwise(versions):
        previous_schema = json.loads((previous_dir / "json-schema.json").read_text())
        current_schema = json.loads((current_dir / "json-schema.json").read_text())
        previous_artifacts = json.loads((previous_dir / "artifact-types.json").read_text())
        current_artifacts = json.loads((current_dir / "artifact-types.json").read_text())
        changes = breaking_changes(previous_schema, current_schema)
        changes.extend(artifact_registry_breaking_changes(previous_artifacts, current_artifacts))
        if changes and current_version[0] <= previous_version[0]:
            errors.append(
                f"breaking changes require a major version bump "
                f"({previous_dir.name} -> {current_dir.name}): {', '.join(changes)}"
            )
    return errors


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
