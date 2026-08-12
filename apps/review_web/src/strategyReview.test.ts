import { buildStrategyReviewView } from "./strategyReview";
import type { StrategyReviewPackage } from "./generated/contracts.generated";

const reference = (artifact_type: string, artifact_id: string) => ({
  artifact_id,
  version: 1,
  artifact_type,
});

const candidate = "00000000-0000-4000-8000-000000000001";
const pkg = {
    comparison_ref: reference("StrategyComparisonPackage", "00000000-0000-4000-8000-000000000010"),
    approved_story_ref: reference("StoryGraph", "00000000-0000-4000-8000-000000000011"),
    effective_config_ref: reference("EffectiveStrategyConfig", "00000000-0000-4000-8000-000000000012"),
    strategy_candidate_set_ref: reference("StrategyCandidateSet", "00000000-0000-4000-8000-000000000013"),
    hook_candidate_set_ref: reference("HookCandidateSet", "00000000-0000-4000-8000-000000000014"),
    allowed_strategy_ids: [candidate],
    allowed_hook_ids: ["00000000-0000-4000-8000-000000000002"],
    blocker_candidate_ids: [candidate],
    candidate_brief_refs: [reference("CreativeBrief", "00000000-0000-4000-8000-000000000015")],
    candidate_variant_plan_refs: [reference("VariantPlan", "00000000-0000-4000-8000-000000000016")],
    incomplete: false,
} as StrategyReviewPackage;
if (buildStrategyReviewView(pkg).approvalEnabled) {
  throw new Error("missing strategy selection must fail closed");
}
if (buildStrategyReviewView(pkg, candidate).approvalEnabled) {
  throw new Error("blocked strategy selection must fail closed");
}
