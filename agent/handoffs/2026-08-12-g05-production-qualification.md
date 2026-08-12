# Handoff — G05 Production Qualification

Handoff ID: `H-2026-08-12-G05`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: Complete an evidence-backed E06 production qualification without synthesizing approval.

Active Epic / Backlog ID: E06 / G05 (human sign-off pending)
Starting State Version: 25

Inputs Read: canonical quality/engineering rules, Stage 2 qualification design, G01-G04 evidence,
Provider/rights decisions and current workspace/runtime.

Decisions Made: ADR-032 makes negative qualification a valid engineering result and reserves approval
for a human after every blocker passes.

Files Changed: Qualification Contract/Registry 1.7.0, deterministic matrix/scripts/tests, bounded
concurrency probe, canary/rollback config, Grafana dashboard, runbook, acceptance report, ADR/State.

Validation Performed:

- `scripts/qualify_e06.py --allow-blocked`: 12 checks; 6 passed, 4 blocked, 2 not evaluated;
  recommendation rejected, decision pending_human.
- `scripts/accept_g05.py`: 16/16 OpenCV research requests with 4 threads, P50 8 ms/P95 17 ms;
  explicitly no production authority.
- Full `make check` and Review Web TypeScript check are required immediately before commit.

Completed: machine-readable qualification, fail-closed approval contract, operational artifacts and
honest negative qualification evidence.

Not Completed: production admission and E06 closure. Blockers are listed in the matrix and report.

Workspace State: G05 evidence intended to be committed; local FunASR may listen on port 7860.

Risks / Blockers / Open Decisions: real corpus, exact model rights, full Mac mini load/fault data and
telemetry drill require new external evidence/authority.

Next Exact Step: project owner reviews `quality/E06_ACCEPTANCE_REPORT.md`; rejection acknowledgement
keeps E06 active, while approval is contract-invalid until all blockers pass.

Project State Update: State Version 26; E06/G05 awaiting human sign-off, not closed.
