# Handoff — G04 Visual Observation

Handoff ID: `H-2026-08-12-G04`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: Complete the replaceable, evidence-bound Visual Observation engineering slice without
claiming unavailable model quality.

Active Epic / Backlog ID: E06 / G05
Starting State Version: 24

Inputs Read: canonical rules, Stage 2 Visual/Benchmark/Acceptance designs, current Provider Gateway,
Registry and G03 handoff.

Decisions Made: ADR-031 freezes typed capability separation, source-frame evidence, Shot-local
tracking, constrained VLM semantics, bounded supplementary sampling and license-first admission.

Files Changed: visual contracts/intelligence/providers/service/workflow/resources/metrics/tests,
Registry 1.6.0, ADR-031, baseline report and Project State.

Validation Performed:

- Visual targeted suite: 9 passed; Ruff and strict mypy passed.
- Review Web direct TypeScript typecheck passed.
- Real ignored demo frame: OpenCV research adapter decoded in 24 ms, emitted 8 foreground candidates
  and explicit quality features; did not claim semantic detection or identity.

Completed: public contracts, application normalization, local and typed HTTP adapters, resource
guard, Temporal registration, capability-specific metrics and tests.

Not Completed: no OCR/detector/tracker/embedding/VLM checkpoint has production license/checksum or
real domain threshold. These are explicit G05 qualification blockers.

Workspace State: G04 intended to be committed independently after full `make check`.

Risks / Blockers / Open Decisions: exact production model choices depend on legal rights, real
benchmark quality and fixed Mac mini resources; Ultralytics cannot be silently admitted.

Next Exact Step: execute G05 qualification matrix, failure/resilience tests, runbook/dashboard,
canary/rollback plan and human acceptance report.

Project State Update: State Version 25.
