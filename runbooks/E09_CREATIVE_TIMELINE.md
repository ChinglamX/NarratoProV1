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
