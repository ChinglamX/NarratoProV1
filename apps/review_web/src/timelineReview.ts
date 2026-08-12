import type { TimelineReviewPackage } from "./generated/contracts.generated";

export type TimelineReviewView = {
  package: TimelineReviewPackage;
  tracks: readonly ["video", "original_audio", "narration", "bgm_sfx", "subtitle", "overlay"];
  tools: readonly ["trim", "split", "move", "replace", "crop", "narration", "rhythm", "undo_redo", "local_preview"];
  approvalEnabled: boolean;
  approvalDisabledReasons: string[];
};

export function buildTimelineReviewView(reviewPackage: TimelineReviewPackage): TimelineReviewView {
  const reasons = [...(reviewPackage.blocker_codes ?? [])];
  if (reviewPackage.incomplete) reasons.push("timeline-package-incomplete");
  if (!reviewPackage.preview_ref) reasons.push("full-preview-required");
  return {
    package: reviewPackage,
    tracks: ["video", "original_audio", "narration", "bgm_sfx", "subtitle", "overlay"],
    tools: ["trim", "split", "move", "replace", "crop", "narration", "rhythm", "undo_redo", "local_preview"],
    approvalEnabled: reasons.length === 0,
    approvalDisabledReasons: reasons,
  };
}
