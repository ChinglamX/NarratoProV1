import { buildTimelineReviewView } from "./timelineReview";
import type { TimelineReviewPackage } from "./generated/contracts.generated";

const blocked = { blocker_codes: ["duration-conflict"], incomplete: false, preview_ref: {} } as unknown as TimelineReviewPackage;
const view = buildTimelineReviewView(blocked);
if (view.approvalEnabled || !view.tools.includes("local_preview")) {
  throw new Error("timeline workspace must fail closed and expose precision tools");
}
