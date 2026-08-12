# Handoff — G03 Speech Observation

Handoff ID: `H-2026-08-12-G03`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: Complete the typed Speech Observation vertical slice without granting production
admission to unlicensed or uncalibrated model weights.

Active Epic / Backlog ID: E06 / G04
Starting State Version: 23

Inputs Read: canonical project/agent/quality/engineering rules, Stage 2 Speech/Benchmark design,
E06 backlog, ADR-028/029, and current workspace/Git state.

Decisions Made: ADR-030 freezes typed Speech boundaries, cluster/identity separation,
research-first FunASR admission, critical conflict behavior, and separate Speech metrics.

Files Changed: Speech contracts/normalizer/provider/service/workflow/tests, Registry 1.5.0,
G03 baseline report, ADR-030 and Project State.

Validation Performed:

- `make check`: 183 tests, 80.55% coverage; Ruff, strict mypy, Bandit, context, architecture and
  registry freshness passed.
- Review Web direct TypeScript `tsc --noEmit`: passed.
- Local adapter on generated Mandarin WAV: research admission, 1 timed segment, 1 speaker cluster,
  1,313 ms, synthetic CER 0.0.

Completed: typed/raw lineage boundary, explicit unavailable, Shadow Confidence, source timing,
speaker observation, critical conflict, metrics, Temporal activity/workflow registration and tests.

Not Completed: production license/checksum approval and real multi-series Speech quality baseline;
these are explicit G05 blockers, not hidden completion claims.

Workspace State: G03 intended to be committed independently; local FunASR may still listen on 7860.

Risks / Blockers / Open Decisions: real legally usable annotated corpus and exact model-weight
rights remain unavailable; do not promote provider from research.

Next Exact Step: implement G04 typed Visual Observation pipeline and research/unavailable adapters.

Project State Update: State Version 24.
