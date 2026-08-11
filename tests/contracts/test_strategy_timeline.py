from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.contracts import (
    CreativeBrief,
    HookCandidate,
    MasterTimeline,
    SellingPoint,
    SellingPointSet,
    StrategyCandidateSet,
    TimelineConflict,
    TimelinePatch,
)


def ref(kind: str) -> dict[str, object]:
    return {"artifact_id": uuid4(), "version": 1, "artifact_type": kind}


def rational(value: int, rate: int = 25) -> dict[str, int]:
    return {"value": value, "rate_num": rate}


def evidence() -> dict[str, object]:
    return {"evidence_id": uuid4(), "source": ref("SourceMedia"), "evidence_type": "visual"}


def confidence() -> dict[str, object]:
    return {
        "score": 0.7,
        "status": "shadow",
        "method": "heuristic-v1",
        "applicable_scope": "strategy:v1",
        "risk_class": "medium",
    }


def selling_point(**overrides: object) -> SellingPoint:
    values: dict[str, object] = {
        "selling_point_id": uuid4(),
        "taxonomy_type": "reversal",
        "description": "被轻视的人揭示真实身份",
        "story_refs": [uuid4()],
        "evidence": [evidence()],
        "audience_rationale": "身份反差建立期待",
        "platform_fit": ["douyin"],
        "narrative_role": "hook",
        "spoiler_level": 1,
        "source_coverage": {"shots": 3},
        "risk_class": "medium",
        "heuristic_components": {"conflict": 0.8},
        "confidence": confidence(),
    }
    values.update(overrides)
    return SellingPoint.model_validate(values)


def hook(**overrides: object) -> HookCandidate:
    values: dict[str, object] = {
        "hook_id": uuid4(),
        "hook_type": "identity-question",
        "opening_promise": "所有人都看不起他, 却没人知道他的身份",
        "source_moment_refs": [uuid4()],
        "visual_intent": {"subject": "protagonist"},
        "audience_question": "他究竟是谁?",
        "duration_budget": rational(75),
        "continuation_beats": [uuid4()],
        "evidence": [evidence()],
        "heuristic_scores": {"comprehension": 0.8},
        "confidence": confidence(),
    }
    values.update(overrides)
    return HookCandidate.model_validate(values)


def direction(strategy_id=None, protagonist_id=None) -> dict[str, object]:
    return {
        "strategy_id": strategy_id or uuid4(),
        "objective": "建立身份反转期待",
        "audience_hypothesis": "偏好逆袭叙事的观众",
        "platform_profile_ref": ref("ConfigArtifact"),
        "genre_config_ref": ref("ConfigArtifact"),
        "primary_selling_point_refs": [uuid4()],
        "protagonist_ref": protagonist_id or uuid4(),
        "viewpoint": "跟随被轻视的主角",
        "opening_promise": "身份即将揭晓",
        "ending_payoff": "主角完成第一次反击",
        "narrative_spine": [
            {
                "beat_id": uuid4(),
                "function": "hook",
                "story_refs": [uuid4()],
                "priority": 100,
                "information_owner": "mixed",
                "required": True,
            }
        ],
        "reveal_policy": {"withhold": "identity"},
        "emotional_curve_intent": ["pressure", "reversal"],
        "target_duration": rational(1500),
        "production_estimate": {"complexity": "medium"},
        "feasible": True,
    }


def test_strategy_contracts_require_evidence_continuation_and_structural_difference() -> None:
    point = selling_point()
    assert SellingPoint.model_validate_json(point.canonical_json()) == point
    point_set = SellingPointSet.model_validate(
        {
            "approved_story_ref": ref("StoryGraph"),
            "taxonomy_version": "1.0.0",
            "selling_points": [point],
        }
    )
    assert SellingPointSet.model_validate_json(point_set.canonical_json()) == point_set
    hook_value = hook()
    assert HookCandidate.model_validate_json(hook_value.canonical_json()) == hook_value
    with pytest.raises(ValidationError, match="story refs and evidence"):
        selling_point(evidence=[])
    with pytest.raises(ValidationError, match="continuation"):
        hook(continuation_beats=[])
    same = direction()
    duplicate = {**same, "strategy_id": uuid4()}
    with pytest.raises(ValidationError, match="structurally"):
        StrategyCandidateSet.model_validate(
            {
                "approved_story_ref": ref("StoryGraph"),
                "selling_point_set_ref": ref("SellingPointSet"),
                "effective_config_ref": ref("EffectiveConfigSnapshot"),
                "candidates": [same, duplicate],
            }
        )


def test_creative_brief_round_trip() -> None:
    brief = CreativeBrief.model_validate(
        {
            "strategy_ref": ref("StrategyCandidateSet"),
            "selected_strategy_id": uuid4(),
            "selected_hook_id": uuid4(),
            "target_duration": rational(1500),
            "narrative_spine": direction()["narrative_spine"],
            "hard_constraints": {"rights": "resolved"},
            "soft_preferences": {"pace": "fast"},
            "approved_by_ref": "review-decision-1",
        }
    )
    assert CreativeBrief.model_validate_json(brief.canonical_json()) == brief


def timeline_item(item_id=None, start=0, duration=25) -> dict[str, object]:
    return {
        "item_id": item_id or uuid4(),
        "item_version": 1,
        "item_type": "clip",
        "timeline_range": {"start": rational(start), "duration": rational(duration)},
        "source_ref": ref("SourceMedia"),
        "source_range": {"start": rational(0), "duration": rational(duration)},
    }


def test_master_timeline_bounds_identity_and_round_trip() -> None:
    value = MasterTimeline.model_validate(
        {
            "timeline_id": uuid4(),
            "lifecycle": "draft",
            "rate_num": 25,
            "global_start": rational(0),
            "duration": rational(100),
            "tracks": [
                {"track_id": uuid4(), "kind": "video", "order": 0, "items": [timeline_item()]}
            ],
            "markers": [
                {
                    "marker_id": uuid4(),
                    "position": rational(25),
                    "marker_type": "beat",
                    "label": "Hook payoff",
                }
            ],
            "metadata_namespace_version": "1.0.0",
        }
    )
    assert MasterTimeline.model_validate_json(value.canonical_json()) == value
    with pytest.raises(ValidationError, match="outside"):
        MasterTimeline.model_validate(
            {
                **value.model_dump(),
                "tracks": [
                    {
                        "track_id": uuid4(),
                        "kind": "video",
                        "order": 0,
                        "items": [timeline_item(start=90, duration=25)],
                    }
                ],
            }
        )
    duplicate_id = uuid4()
    with pytest.raises(ValidationError, match="globally unique"):
        MasterTimeline.model_validate(
            {
                **value.model_dump(),
                "tracks": [
                    {
                        "track_id": uuid4(),
                        "kind": "video",
                        "order": 0,
                        "items": [timeline_item(duplicate_id)],
                    },
                    {
                        "track_id": uuid4(),
                        "kind": "narration",
                        "order": 1,
                        "items": [timeline_item(duplicate_id)],
                    },
                ],
            }
        )


def test_timeline_patch_requires_cas_and_nonempty_operations() -> None:
    target_id = uuid4()
    patch = TimelinePatch.model_validate(
        {
            "patch_id": uuid4(),
            "base_timeline": ref("MasterTimeline"),
            "operations": [
                {
                    "operation_id": uuid4(),
                    "op": "trim",
                    "target_item_id": target_id,
                    "expected_item_version": 1,
                    "payload": {"end": 10},
                }
            ],
            "author": {"kind": "human", "id": "editor"},
            "reason": "tighten hook",
        }
    )
    assert TimelinePatch.model_validate_json(patch.canonical_json()) == patch
    conflict = TimelineConflict.model_validate(
        {
            "conflict_id": uuid4(),
            "patch_ref": ref("PatchProposal"),
            "base_timeline_ref": ref("MasterTimeline"),
            "current_timeline_ref": ref("MasterTimeline"),
            "operation_id": patch.operations[0].operation_id,
            "conflict_type": "stale-item-version",
            "expected_item_version": 1,
            "actual_item_version": 2,
        }
    )
    assert TimelineConflict.model_validate_json(conflict.canonical_json()) == conflict
    with pytest.raises(ValidationError, match="requires target"):
        TimelinePatch.model_validate(
            {
                "patch_id": uuid4(),
                "base_timeline": ref("MasterTimeline"),
                "operations": [{"operation_id": uuid4(), "op": "trim", "payload": {"end": 10}}],
                "author": {"kind": "human", "id": "editor"},
                "reason": "tighten hook",
            }
        )
    with pytest.raises(ValidationError, match="at least one"):
        TimelinePatch.model_validate(
            {
                "patch_id": uuid4(),
                "base_timeline": ref("MasterTimeline"),
                "operations": [],
                "author": {"kind": "human", "id": "editor"},
                "reason": "empty",
            }
        )
