"""Persist three Episode 8 strategy candidates and open the L1 Gate 2 review."""

# ruff: noqa: RUF001 - Chinese punctuation is intentional in review copy.

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Connection

from packages.contracts import (
    ActorRef,
    ApprovedCreativeBrief,
    ArtifactRef,
    CandidateBudget,
    CandidateDisposition,
    CandidateEvaluation,
    CandidateValidation,
    ConfidenceRecord,
    CostEstimate,
    DiversityPair,
    DiversityReport,
    FeasibilityReport,
    HookCandidate,
    HookCandidateSet,
    NarrativeBeatIntent,
    SellingPoint,
    SellingPointSet,
    StoryGraph,
    StrategyCandidateSet,
    StrategyComparisonPackage,
    StrategyDirection,
    StrategyReviewPackage,
    VariantPlan,
    VariantSpec,
)
from packages.foundation.settings import get_settings
from packages.persistence import ArtifactRepository
from packages.persistence.artifact_writer import commit_contract_artifact
from packages.persistence.database import create_database_engine
from packages.persistence.review_repository import ReviewRepository

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("dd397853-79bc-4e6f-a540-bb1c296d6936")
RUN_ID = UUID("136b8fe5-180a-4159-8097-5f688e155305")
TRACE_ID = "8e003000000000000000000000000003"
STORY_REF = ArtifactRef.model_validate(
    {
        "artifact_id": "c378ba51-da33-4049-baf0-538ca637e9a5",
        "version": 1,
        "artifact_type": "StoryGraph",
        "checksum": "sha256:8b34ae0d15d81126a1907366e27efcb4ce113e5bea0e1d2fae0ec146d0c7aad2",
    }
)


def ref(artifact_id: UUID, artifact_type: str) -> ArtifactRef:
    return ArtifactRef.model_validate(
        {"artifact_id": artifact_id, "version": 1, "artifact_type": artifact_type}
    )


def commit(
    connection: Connection,
    artifacts: ArtifactRepository,
    *,
    artifact_id: UUID,
    artifact_type: str,
    payload: Any,
    inputs: tuple[ArtifactRef, ...],
    config_ref: ArtifactRef,
) -> ArtifactRef:
    return commit_contract_artifact(
        connection,
        artifacts,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        payload=payload,
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        variant_id=None,
        trace_id=TRACE_ID,
        actor=ActorRef.model_validate({"kind": "model", "id": "codex-producer"}),
        producer_module="vc003-episode08-strategy-candidates",
        module_version="1.0.0",
        resource_profile_ref=config_ref,
        rights_class="internal-only",
        inputs=inputs,
        schema_version="2.6.0",
    )


def main() -> int:
    engine = create_database_engine(get_settings().database_url)
    artifacts, reviews = ArtifactRepository(), ReviewRepository()
    with engine.connect() as connection:
        row = artifacts.get_version(connection, STORY_REF)
        approved = reviews.approved_story(connection, project_id=PROJECT_ID)
    if row["checksum"] != str(STORY_REF.checksum):
        raise RuntimeError("approved Story checksum drift")
    if approved is None or str(approved["artifact_id"]) != str(STORY_REF.artifact_id):
        raise RuntimeError("VC-003 requires the exact approved Story pointer")
    story = StoryGraph.model_validate(row["payload_json"])
    if len(story.events) != 3:
        raise RuntimeError("VC-003 Episode 8 pack expects exactly three reviewed events")

    confidence = ConfidenceRecord.model_validate(
        {
            "score": None,
            "status": "unavailable",
            "method": "human-reviewed-story-to-strategy-candidate-v1",
            "applicable_scope": "episode-08:strategy-candidates:l1-gate2",
            "risk_class": "high",
            "evidence": [
                evidence.model_dump(mode="json")
                for event in story.events
                for evidence in event.evidence
            ],
            "opposing_factors": [
                {
                    "code": "marketing-performance-unavailable",
                    "description": "No exposure or retention data exists for these directions.",
                }
            ],
        }
    )
    budget = CandidateBudget(
        max_selling_points=3,
        max_strategy_directions=3,
        max_hooks_per_direction=1,
        max_total_candidates=3,
        max_revision_rounds=1,
        max_model_tokens=0,
        max_estimated_cost_micros=0,
    )
    ids = {name: uuid4() for name in ("config", "points", "strategies", "hooks", "comparison")}
    config_placeholder = ref(ids["config"], "EffectiveConfigSnapshot")
    point_ids = [uuid4() for _ in story.events]
    points = SellingPointSet(
        approved_story_ref=STORY_REF,
        taxonomy_version="vc003-episode08-v1",
        selling_points=tuple(
            SellingPoint.model_validate(
                {
                    "selling_point_id": point_id,
                    "taxonomy_type": taxonomy,
                    "description": event.description,
                    "story_refs": [event.event_id],
                    "evidence": [item.model_dump(mode="json") for item in event.evidence],
                    "audience_rationale": rationale,
                    "platform_fit": ["vertical-short-video"],
                    "narrative_role": "core",
                    "spoiler_level": spoiler,
                    "source_coverage": {"event_count": 1},
                    "risk_class": "high",
                    "heuristic_components": {"evidence_coverage": 1.0},
                    "confidence": confidence.model_dump(mode="json"),
                    "assumptions": ["Marketing relevance requires Gate 2 human judgment"],
                }
            )
            for point_id, event, taxonomy, rationale, spoiler in zip(
                point_ids,
                story.events,
                ("transaction", "payment-detail", "retaliation-threat"),
                (
                    "A concrete high-value transaction can establish immediate stakes.",
                    "The bank-card detail makes the value transfer tangible.",
                    "The retaliation threat creates danger and continuation pressure.",
                ),
                (1, 1, 2),
                strict=True,
            )
        ),
    )

    labels = ("威胁倒叙", "三十万交易", "财富引爆危机")
    descriptions = (
        "先抛出追杀威胁，再倒叙三十万交易，主打危险悬念。",
        "按交易成交、银行卡交付、消息泄露到威胁的顺序，主打清晰升级。",
        "先用三十万与六个八密码制造具体记忆点，再揭示财富触发报复。",
    )
    orders = ((2, 0, 1), (0, 1, 2), (1, 2, 0))
    functions = (
        ("danger-hook", "transaction-context", "value-proof"),
        ("transaction-hook", "payment-proof", "threat-escalation"),
        ("value-hook", "retaliation-escalation", "transaction-context"),
    )
    strategies: list[StrategyDirection] = []
    hooks: list[HookCandidate] = []
    strategy_ids: list[UUID] = []
    hook_ids: list[UUID] = []
    for label, description, order, beat_functions in zip(
        labels, descriptions, orders, functions, strict=True
    ):
        strategy_id, hook_id = uuid4(), uuid4()
        strategy_ids.append(strategy_id)
        hook_ids.append(hook_id)
        beats = tuple(
            NarrativeBeatIntent(
                beat_id=uuid4(),
                function=function,
                story_refs=(story.events[index].event_id,),
                priority=100 - position * 10,
                information_owner="mixed",
                required=True,
            )
            for position, (index, function) in enumerate(zip(order, beat_functions, strict=True))
        )
        strategies.append(
            StrategyDirection.model_validate(
                {
                    "strategy_id": strategy_id,
                    "objective": description,
                    "audience_hypothesis": "偏好高价值交易、利益冲突与追杀悬念的短剧观众。",
                    "platform_profile_ref": config_placeholder,
                    "genre_config_ref": config_placeholder,
                    "primary_selling_point_refs": [point_ids[order[0]]],
                    "secondary_selling_point_refs": [point_ids[i] for i in order[1:]],
                    "protagonist_ref": story.events[0].event_id,
                    "viewpoint": "未命名交易获得者；不宣称 canonical character identity。",
                    "opening_promise": label,
                    "ending_payoff": "兑现三十万交易如何引爆盯梢与死亡威胁。",
                    "narrative_spine": [beat.model_dump(mode="json") for beat in beats],
                    "reveal_policy": {"order": list(order), "identity": "withhold-unproven"},
                    "emotional_curve_intent": ["curiosity", "value", "danger"],
                    "target_duration": {"value": 30, "rate_num": 1},
                    "assumptions": ["人物身份保持未知", "实际选镜在 Gate 2 后执行"],
                    "risks": ["identity-unresolved", "performance-unavailable"],
                    "production_estimate": {"complexity": "low", "source_episode": 8},
                    "feasible": True,
                }
            )
        )
        opening_event = story.events[order[0]]
        hooks.append(
            HookCandidate.model_validate(
                {
                    "hook_id": hook_id,
                    "hook_type": beat_functions[0],
                    "opening_promise": description,
                    "source_moment_refs": [opening_event.event_id],
                    "visual_intent": {"source_event": str(opening_event.event_id)},
                    "narration_or_dialogue": opening_event.description,
                    "audio_intent": {"preserve_original_dialogue": True},
                    "disclosed_information": [opening_event.description],
                    "withheld_information": ["人物 canonical identity", "威胁是否兑现"],
                    "audience_question": "这笔三十万交易为什么会招来追杀？",
                    "duration_budget": {"value": 4, "rate_num": 1},
                    "continuation_beats": [story.events[i].event_id for i in order[1:]],
                    "evidence": [item.model_dump(mode="json") for item in opening_event.evidence],
                    "assumptions": ["Hook attraction is uncalibrated"],
                    "risks": ["performance-unavailable"],
                    "heuristic_scores": {"evidence_coverage": 1.0},
                    "confidence": confidence.model_dump(mode="json"),
                }
            )
        )

    with engine.begin() as connection:
        config_ref = commit(
            connection,
            artifacts,
            artifact_id=ids["config"],
            artifact_type="EffectiveConfigSnapshot",
            payload={
                "scope": "episode-08-gate2-candidates",
                "automation_level": "L1",
                "target_duration_seconds": 30,
                "platform": "vertical-short-video",
                "candidate_budget": budget.model_dump(mode="json"),
                "confidence": "unavailable",
            },
            inputs=(STORY_REF,),
            config_ref=config_placeholder,
        )
        points_ref = commit(
            connection,
            artifacts,
            artifact_id=ids["points"],
            artifact_type="SellingPointSet",
            payload=points,
            inputs=(STORY_REF,),
            config_ref=config_ref,
        )
        strategy_set = StrategyCandidateSet(
            approved_story_ref=STORY_REF,
            selling_point_set_ref=points_ref,
            effective_config_ref=config_ref,
            candidates=tuple(strategies),
        )
        strategies_ref = commit(
            connection,
            artifacts,
            artifact_id=ids["strategies"],
            artifact_type="StrategyCandidateSet",
            payload=strategy_set,
            inputs=(STORY_REF, points_ref, config_ref),
            config_ref=config_ref,
        )
        hook_set = HookCandidateSet(
            approved_story_ref=STORY_REF,
            strategy_candidate_set_ref=strategies_ref,
            candidates=tuple(hooks),
            validations=tuple(
                CandidateValidation(
                    candidate_id=item.hook_id,
                    disposition=CandidateDisposition.VALID,
                )
                for item in hooks
            ),
        )
        hooks_ref = commit(
            connection,
            artifacts,
            artifact_id=ids["hooks"],
            artifact_type="HookCandidateSet",
            payload=hook_set,
            inputs=(STORY_REF, strategies_ref),
            config_ref=config_ref,
        )
        evaluations = tuple(
            CandidateEvaluation(
                candidate_id=item.strategy_id,
                disposition=CandidateDisposition.VALID,
                deterministic_blockers=(),
                critic_results=(),
                risks=(),
                feasibility=FeasibilityReport(
                    candidate_id=item.strategy_id,
                    feasible=True,
                    source_coverage=1.0,
                    duration_feasible=True,
                    production_complexity=1,
                    reasons=("All three approved Story events fit the 30-second intent budget.",),
                ),
                cost=CostEstimate(
                    method_version="candidate-only-v1",
                    resource_profile_ref=config_ref,
                    minimum_micros=0,
                    maximum_micros=0,
                    estimated_review_seconds=180,
                    components_micros={"generation": 0},
                ),
                heuristic_scores={"evidence_coverage": 1.0},
            )
            for item in strategies
        )
        evaluation_refs = tuple(
            commit(
                connection,
                artifacts,
                artifact_id=uuid4(),
                artifact_type="EvaluationRun",
                payload=item,
                inputs=(strategies_ref, hooks_ref),
                config_ref=config_ref,
            )
            for item in evaluations
        )
        pairs = tuple(
            DiversityPair(
                left_candidate_id=strategies[left].strategy_id,
                right_candidate_id=strategies[right].strategy_id,
                differing_dimensions=("primary_selling_point", "narrative_spine", "reveal_policy"),
                duplicate=False,
                explanation="候选采用不同开场事件、信息顺序和披露策略。",
            )
            for left, right in combinations(range(3), 2)
        )
        comparison = StrategyComparisonPackage(
            approved_story_ref=STORY_REF,
            effective_config_ref=config_ref,
            selling_point_set_ref=points_ref,
            strategy_candidate_set_ref=strategies_ref,
            hook_candidate_set_ref=hooks_ref,
            evaluation_refs=evaluation_refs,
            evaluations=evaluations,
            diversity=DiversityReport(candidate_set_ref=strategies_ref, pairs=pairs),
            blocker_candidate_ids=(),
        )
        comparison_ref = commit(
            connection,
            artifacts,
            artifact_id=ids["comparison"],
            artifact_type="StrategyComparisonPackage",
            payload=comparison,
            inputs=(STORY_REF, config_ref, points_ref, strategies_ref, hooks_ref, *evaluation_refs),
            config_ref=config_ref,
        )
        brief_refs: list[ArtifactRef] = []
        variant_refs: list[ArtifactRef] = []
        for strategy, hook in zip(strategies, hooks, strict=True):
            brief_id = uuid4()
            brief_placeholder = ref(brief_id, "CreativeBrief")
            brief = ApprovedCreativeBrief(
                approved_story_ref=STORY_REF,
                effective_config_ref=config_ref,
                strategy_candidate_set_ref=strategies_ref,
                hook_candidate_set_ref=hooks_ref,
                selected_strategy_id=strategy.strategy_id,
                selected_hook_id=hook.hook_id,
                platform_profile_ref=config_ref,
                audience_profile_ref=config_ref,
                duration_profile_ref=config_ref,
                quality_profile_ref=config_ref,
                target_duration=strategy.target_duration,
                narrative_spine=strategy.narrative_spine,
                visual_intent=hook.visual_intent,
                rhythm_intent={"curve": list(strategy.emotional_curve_intent)},
                narration_intent={"identity_policy": "do-not-name-unproven-characters"},
                audio_intent=hook.audio_intent,
                subtitle_intent={"language": "zh-CN"},
                hard_constraints={"story_ref": str(STORY_REF.artifact_id)},
                soft_preferences={"direction": strategy.objective},
                must_use_story_refs=tuple(
                    ref_id for beat in strategy.narrative_spine for ref_id in beat.story_refs
                ),
                must_avoid=("invented identity", "unsupported causality"),
                accepted_risks=("identity-unresolved", "performance-unavailable"),
                cost_ceiling_micros=0,
            )
            brief_ref = commit(
                connection,
                artifacts,
                artifact_id=brief_id,
                artifact_type="CreativeBrief",
                payload=brief,
                inputs=(comparison_ref, strategies_ref, hooks_ref),
                config_ref=config_ref,
            )
            variant = VariantPlan(
                creative_brief_ref=brief_ref,
                variants=(
                    VariantSpec(
                        variant_id=uuid4(),
                        label="control",
                        control=True,
                        changed_dimensions={},
                        estimated_incremental_cost_micros=0,
                    ),
                ),
                budget_micros=0,
            )
            variant_ref = commit(
                connection,
                artifacts,
                artifact_id=uuid4(),
                artifact_type="VariantPlan",
                payload=variant,
                inputs=(brief_placeholder,),
                config_ref=config_ref,
            )
            brief_refs.append(brief_ref)
            variant_refs.append(variant_ref)
        package = StrategyReviewPackage(
            comparison_ref=comparison_ref,
            approved_story_ref=STORY_REF,
            effective_config_ref=config_ref,
            strategy_candidate_set_ref=strategies_ref,
            hook_candidate_set_ref=hooks_ref,
            allowed_strategy_ids=tuple(strategy_ids),
            allowed_hook_ids=tuple(hook_ids),
            blocker_candidate_ids=(),
            candidate_brief_refs=tuple(brief_refs),
            candidate_variant_plan_refs=tuple(variant_refs),
        )
        review_id = uuid4()
        reviews.create_request(
            connection,
            review_id=review_id,
            project_id=PROJECT_ID,
            workflow_id=f"vc003-gate2/{review_id}",
            gate="strategy",
            target_ref=comparison_ref.model_dump(mode="json"),
            policy_snapshot={
                "automation_level": "L1",
                "strategy_review_package": package.model_dump(mode="json"),
            },
        )

    result = {
        "review_id": str(review_id),
        "state": "awaiting_review",
        "comparison_ref": comparison_ref.model_dump(mode="json", exclude_none=True),
        "approved_story_ref": STORY_REF.model_dump(mode="json", exclude_none=True),
        "candidates": [
            {
                "option": index + 1,
                "label": label,
                "strategy_id": str(strategy.strategy_id),
                "hook_id": str(hook.hook_id),
                "description": description,
                "opening": story.events[order[0]].description,
                "order": [story.events[i].description for i in order],
                "brief_ref": brief_ref.model_dump(mode="json", exclude_none=True),
                "variant_plan_ref": variant_ref.model_dump(mode="json", exclude_none=True),
                "blockers": [],
            }
            for index, (
                label,
                strategy,
                hook,
                description,
                order,
                brief_ref,
                variant_ref,
            ) in enumerate(
                zip(
                    labels,
                    strategies,
                    hooks,
                    descriptions,
                    orders,
                    brief_refs,
                    variant_refs,
                    strict=True,
                )
            )
        ],
        "shared_risks": [
            "人物身份未证明，候选均不得给角色命名。",
            "无真实发布效果数据，吸引力未校准，必须由 Gate 2 人工选择。",
        ],
    }
    output = ROOT / "outputs/vc003_episode_08/gate2_candidates.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
