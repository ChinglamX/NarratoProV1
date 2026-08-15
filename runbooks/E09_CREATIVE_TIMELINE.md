# E09 Creative Timeline Runbook

1. Load only project Approved Creative Brief/Variant Plan and exact Approved Story/Media refs.
2. Fail on hard profile conflict or missing approved pointer.
3. Retrieve per Beat from Evidence ranges first; embedding is recall only.
4. Never fill CoverageGap with unrelated footage; rights-blocked candidates are ineligible.
5. Reconcile minimum/target/maximum Beat budgets before clip or narration compression.
6. Narration factual lines require Story/Evidence and must complement rather than echo dialogue.
7. Crop must remain normalized and preserve key face/action/text; use explicit fallback when infeasible.
8. Compile all intents into one Master Timeline; no module-private final time coordinate.
9. Human edits use semantic Patch/CAS and locks; stale overlapping edits conflict.
10. Review complete playback before checkpoint; E10 consumes only the approved intent pointer.
11. Build the reference benchmark with `python scripts/build_e09_demo_benchmark.py <demo> evaluation/benchmarks/e09_demo_v1.json`; machine features never substitute for human full playback.
12. A missing Approved Story/Brief, failed Preview, Worker replay gap, semantic provider block or unsigned checkpoint keeps E09 active; do not advance to E10.
13. J02/J03/J04 planning products (ClipCandidateSet, ClipSelectionPlan, ContinuityReport, VisualPlanningReport, RhythmPlan, NarrationPlanningReport, TimelineAssemblyReport, SourceSubtitleHandlingPlan) are immutable Artifacts committed through ArtifactRepository with exact-version input edges; never recompute them silently outside the repository boundary.
14. Clip retrieval reads committed ClipCandidateSet payloads through the persistence adapter with route scores and top-k; a source_range exceeding the probed media duration is ineligible. HUMAN_PIN route returns nothing without pinned candidates — fail closed.
15. DurationConflict disposition is human-only: remove-non-core-beat, change-expression or return-to-gate-2; the workflow blocks with duration-infeasible and commits no RhythmPlan.
16. Narration text is only sourced from human-approved NarrationLineSet artifacts (L1); no provider may fabricate narration until production-admitted. Locked lines cannot be regenerated.
17. Assembly must compile into one Master Timeline; a video-duration-mismatch is a blocker and commits only the TimelineAssemblyReport. Original audio and subtitle intents are deterministic projections, never creative additions; BGM/SFX stay absent until rights-cleared assets are admitted.
18. The preview must be media-grounded: real source files trimmed to exact source_range, scaled/padded to the platform frame and concatenated in timeline order; lavfi synthesis is test-only. Missing source media fails the activity.
19. CreativeTimelineWorkflow is fail-closed: coverage-incomplete, duration-infeasible, narration blockers or assembly blockers stop the run at stage boundary with blocked_codes; only an approve review decision ends succeeded, revise returns revision_required.
20. All workflow artifact identities are pre-allocated in the request payloads; retries and replays must converge on the same artifact checksums. Preview identity is deterministic over the timeline ref.
21. Long media preview renders must keep the activity alive: `render_media_preview` accepts a progress callback invoked after each clip; the Temporal activity forwards it through `loop.call_soon_threadsafe(activity.heartbeat, ...)` because the renderer runs in a worker thread with no event loop. Never drop periodic heartbeats on multi-clip renders (30s heartbeat timeout).
22. Multi-variant certification (`scripts/accept_e09_multi_variant.py`) starts two CreativeTimelineWorkflow variants concurrently, hard-restarts the worker, and replays both histories; both must resume at the human checkpoint. Run it after any creative_workflow/activity change to keep the restart/replay blocker closed on the engineering side.
