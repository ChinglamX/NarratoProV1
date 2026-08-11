from datetime import UTC, datetime
from uuid import UUID as PyUUID
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    ActorKind,
    ActorRef,
    ApplicableScope,
    ArtifactRef,
    ArtifactType,
    CalibrationArtifact,
    CalibrationLifecycle,
    ConfidenceRecord,
    ConfidenceStatus,
    Correction,
    DatasetManifest,
    DatasetSplitManifest,
    EvaluationRun,
    EvaluationStatus,
    QualityEvent,
    RiskClass,
    RoutingDecision,
)

NOW = datetime(2026, 8, 12, 8, 0, tzinfo=UTC)


def ref(artifact_type: str, *, artifact_id: PyUUID | None = None, version: int = 1) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id or uuid4(),
        version=version,
        artifact_type=ArtifactType(artifact_type),
    )


def confidence(status: str = "calibrated") -> ConfidenceRecord:
    return ConfidenceRecord(
        score=None if status == "unavailable" else 0.91,
        status=ConfidenceStatus(status),
        method="isotonic-v1" if status != "unavailable" else "detector-unavailable",
        calibration_version="cal-v1" if status in {"calibrated", "drifted"} else None,
        applicable_scope="story.event:qwen-v1:revenge:zh:douyin",
        risk_class=RiskClass.LOW,
    )


def scope() -> ApplicableScope:
    return ApplicableScope(
        module="story",
        task="event-extraction",
        output_type="StoryGraph",
        provider="local",
        model_version="qwen-v1",
        prompt_version="story-v3",
        config_version="genre-v2",
        schema_version="1.1.0",
        genres=frozenset({"revenge"}),
        languages=frozenset({"zh-CN"}),
        platforms=frozenset({"douyin"}),
        risk_classes=frozenset({RiskClass.LOW}),
    )


@pytest.mark.parametrize(
    ("severity", "blocker", "valid"),
    [
        ("S0", True, True),
        ("S0", False, False),
        ("S1", False, True),
        ("S2", False, True),
        ("S3", False, True),
        ("S3", True, False),
    ],
)
def test_quality_event_severity_semantics(severity: str, blocker: bool, valid: bool) -> None:
    values = {
        "event_id": uuid4(),
        "module": "story",
        "dimension": "correctness",
        "issue_type": "causal-wrong",
        "severity": severity,
        "blocker": blocker,
        "target": ref("StoryGraph"),
        "detector": "story-critic",
        "detector_version": "1.0.0",
        "confidence": confidence("shadow"),
        "status": "detected",
        "occurred_at": NOW,
    }
    if valid:
        assert QualityEvent.model_validate(values).severity.value == severity
    else:
        with pytest.raises(ValidationError):
            QualityEvent.model_validate(values)


def test_quality_event_preserves_unresolved_and_disagreement() -> None:
    base = {
        "event_id": uuid4(),
        "module": "story",
        "dimension": "correctness",
        "issue_type": "identity",
        "severity": "S1",
        "blocker": False,
        "target": ref("StoryGraph"),
        "detector": "ensemble",
        "detector_version": "1",
        "confidence": confidence("shadow"),
        "status": "unresolved",
        "occurred_at": NOW,
    }
    unresolved = QualityEvent.model_validate(base)
    assert unresolved.status.value == "unresolved"
    with pytest.raises(ValidationError, match="resolved reviewer label"):
        QualityEvent.model_validate({**base, "reviewer_label": "correct"})
    disputed = QualityEvent.model_validate(
        {**base, "reviewer_label": "disputed", "disagreement": True}
    )
    assert disputed.disagreement


def test_correction_requires_new_version_and_training_consent() -> None:
    artifact_id = uuid4()
    values = {
        "correction_id": uuid4(),
        "project_id": uuid4(),
        "run_id": uuid4(),
        "module": "story",
        "dimension": "correctness",
        "correction_type": "causal-wrong",
        "target_before": ref("StoryGraph", artifact_id=artifact_id, version=1),
        "target_after": ref("StoryGraph", artifact_id=artifact_id, version=2),
        "semantic_operation": {"op": "replace", "path": "/events/2/cause"},
        "before": "guess",
        "after": "supported",
        "reason_taxonomy": ["causal-wrong"],
        "reason": "Evidence shows the opposite causal direction.",
        "severity": "S0",
        "blocker": True,
        "config_version": "cfg-v1",
        "profile_version": "profile-v1",
        "policy_version": "policy-v1",
        "reviewer": ActorRef(kind=ActorKind.HUMAN, id="reviewer-1"),
        "created_at": NOW,
        "eligibility": "evaluation_only",
        "consent_recorded": False,
    }
    correction = Correction.model_validate(values)
    restored = Correction.model_validate_json(correction.model_dump_json())
    assert restored.target_after.version == 2
    with pytest.raises(ValidationError, match="newer artifact version"):
        Correction.model_validate({**values, "target_after": values["target_before"]})
    with pytest.raises(ValidationError, match="recorded consent"):
        Correction.model_validate({**values, "eligibility": "training"})


def test_dataset_calibration_and_evaluation_lineage_round_trip() -> None:
    dataset_id = uuid4()
    manifest = DatasetManifest(
        dataset=ref("DatasetManifest", artifact_id=dataset_id, version=2),
        parent=ref("DatasetManifest", artifact_id=dataset_id, version=1),
        version="2.0",
        split_manifest=DatasetSplitManifest(manifest_id="split", version="2", items=()),
        correction_refs=(ref("CorrectionDataset"),),
        guideline_refs=(ref("QualityReview"),),
        taxonomy_version="2",
        source_schema_version="1.1.0",
        generated_by_version="build-v2",
        content_checksum="sha256:" + "a" * 64,
        created_at=NOW,
    )
    assert DatasetManifest.model_validate_json(manifest.canonical_json()) == manifest

    run_ref = ref("EvaluationRun")
    calibration = CalibrationArtifact(
        calibration=ref("CalibrationArtifact"),
        version="1",
        status=CalibrationLifecycle.APPROVED,
        method="isotonic",
        scope=scope(),
        dataset_ref=manifest.dataset,
        evaluation_run_ref=run_ref,
        feature_schema_version="1",
        code_version="git-abc",
        metrics={"ece": 0.03},
        approved_by=ActorRef(kind=ActorKind.HUMAN, id="review-director"),
        approved_at=NOW,
        created_at=NOW,
    )
    assert CalibrationArtifact.model_validate_json(calibration.canonical_json()) == calibration

    evaluation = EvaluationRun(
        evaluation=run_ref,
        plan_ref=ref("ExperimentPlan"),
        candidate_ref=ref("ConfigArtifact", version=2),
        champion_ref=ref("ConfigArtifact"),
        dataset_ref=manifest.dataset,
        applicable_slices=("causal",),
        metric_versions={"ece": "1"},
        blocker_gates=("s0-miss",),
        code_version="git-abc",
        dependency_lock_checksum="sha256:" + "b" * 64,
        seed=7,
        status=EvaluationStatus.COMPLETED,
        result_refs=(ref("ExperimentResult"),),
        started_at=NOW,
        completed_at=NOW,
    )
    assert EvaluationRun.model_validate_json(evaluation.canonical_json()) == evaluation


def routing(**overrides: object) -> RoutingDecision:
    values: dict[str, object] = {
        "decision": ref("RoutingDecision"),
        "target": ref("StoryGraph"),
        "gate": "story",
        "automation_level": "L2",
        "effective_policy_ref": ref("AutomationPolicy"),
        "calibration_ref": ref("CalibrationArtifact"),
        "scope": scope(),
        "confidence": confidence(),
        "required_checks_complete": True,
        "has_blocker": False,
        "has_rights_risk": False,
        "has_conflict": False,
        "has_unresolved": False,
        "has_disagreement": False,
        "outcome": "auto_flow",
        "reasons": ("approved scope",),
        "decided_at": NOW,
    }
    values.update(overrides)
    return RoutingDecision.model_validate(values)


def test_routing_fails_closed_for_shadow_unavailable_and_ambiguity() -> None:
    assert routing().outcome.value == "auto_flow"
    for status in ("shadow", "unavailable", "drifted"):
        with pytest.raises(ValidationError, match="must require review"):
            routing(confidence=confidence(status))
    for field in (
        "has_blocker",
        "has_rights_risk",
        "has_conflict",
        "has_unresolved",
        "has_disagreement",
    ):
        with pytest.raises(ValidationError, match="must require review"):
            routing(**{field: True})
    with pytest.raises(ValidationError, match="must require review"):
        routing(gate="release")
    assert (
        routing(confidence=confidence("unavailable"), outcome="required_review").outcome.value
        == "required_review"
    )
