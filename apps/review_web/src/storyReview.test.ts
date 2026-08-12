import { buildStoryReviewView } from "./storyReview";
import type { StoryReviewPackage } from "./generated/contracts.generated";

const blocked = {
  blocker_codes: ["identity-conflict"],
  incomplete: false,
  unresolved_count: 0,
} as unknown as StoryReviewPackage;

if (buildStoryReviewView(blocked).approvalEnabled) {
  throw new Error("blocked story must not enable approval");
}
