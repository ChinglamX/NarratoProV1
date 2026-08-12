import type {
  StrategyReviewPackage,
} from "./generated/contracts.generated";

export type StrategyReviewView = {
  package: StrategyReviewPackage;
  tabs: readonly ["candidates", "hooks", "evidence", "diversity", "risks", "cost"];
  selectedStrategyId?: string;
  approvalEnabled: boolean;
  approvalDisabledReasons: string[];
};

export function buildStrategyReviewView(
  reviewPackage: StrategyReviewPackage,
  selectedStrategyId?: string,
): StrategyReviewView {
  const reasons: string[] = [];
  if (reviewPackage.incomplete) reasons.push("strategy-package-incomplete");
  if (!selectedStrategyId) reasons.push("strategy-selection-required");
  if (selectedStrategyId && (reviewPackage.blocker_candidate_ids ?? []).includes(selectedStrategyId)) {
    reasons.push("selected-strategy-blocked");
  }
  if (selectedStrategyId && !reviewPackage.allowed_strategy_ids.includes(selectedStrategyId)) {
    reasons.push("selected-strategy-outside-package");
  }
  return {
    package: reviewPackage,
    tabs: ["candidates", "hooks", "evidence", "diversity", "risks", "cost"],
    selectedStrategyId,
    approvalEnabled: reasons.length === 0,
    approvalDisabledReasons: reasons,
  };
}
