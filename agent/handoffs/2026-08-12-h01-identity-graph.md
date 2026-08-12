# Handoff — H01 Identity Graph Domain

Handoff ID: `H-2026-08-12-H01-IDENTITY`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: Implement a conservative, evidence-grounded identity domain without treating similarity
as identity.

Active Epic / Backlog ID: E07 / H02
Starting State Version: 27

Inputs Read: canonical project/agent/quality/engineering files, E07 Epic, Stage 2 Identity design,
frozen Speech/Visual Observation contracts and E06 qualification evidence.

Decisions Made: ADR-033; similarity is review-only, human corrected-same is merge authority,
cannot-link wins, unknown identities remain temporary, and replay callers inject allocated UUIDv4 IDs.

Files Changed: identity contracts and assembly, Contract exports/Registry 1.8.0/generated outputs,
contract and intelligence tests, ADR, Project State and this handoff.

Validation Performed: targeted pytest, Ruff, strict mypy, Registry generation/freshness, full project
check and Review Web TypeScript check.

Completed: H01 engineering contracts and conservative assembly.

Not Completed: persistence, Review API, invalidation, model calibration and real-data identity quality.

Workspace State: H01 committed checkpoint; see Git history.

Risks / Blockers / Open Decisions: synthetic fixtures cannot establish cross-episode identity quality;
E06 provider qualification remains rejected/pending human.

Next Exact Step: implement H02 persistence, immutable review correction and dependency invalidation.

Project State Update: State Version 28.
