import type { StoryReviewPackage } from "./generated/contracts.generated";

export type StoryReviewView = {
  package: StoryReviewPackage;
  tabs: readonly ["events", "identities", "states", "causality", "evidence", "risks"];
  approvalEnabled: boolean;
  approvalDisabledReasons: string[];
};

export function buildStoryReviewView(reviewPackage: StoryReviewPackage): StoryReviewView {
  const reasons = [...(reviewPackage.blocker_codes ?? [])];
  if (reviewPackage.incomplete) reasons.push("story-incomplete");
  if ((reviewPackage.unresolved_count ?? 0) > 0) reasons.push("unresolved-items-require-review");
  return {
    package: reviewPackage,
    tabs: ["events", "identities", "states", "causality", "evidence", "risks"],
    approvalEnabled: reasons.length === 0,
    approvalDisabledReasons: reasons,
  };
}
