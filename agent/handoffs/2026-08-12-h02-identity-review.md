# Handoff — H02 Identity Persistence, Review and Invalidation

Handoff ID: `H-2026-08-12-H02-IDENTITY-REVIEW`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: Persist human identity corrections as serialized immutable successors and precisely
invalidate explicit downstream dependencies.

Active Epic / Backlog ID: E07 / H03
Starting State Version: 28

Inputs Read: H01 contracts/ADR, Stage 1 persistence/review primitives and Stage 2 identity/review design.

Decisions Made: ADR-034; preview before commit, reviewer RBAC, Project advisory lock, active-pointer
CAS, applied proposal lineage and exact dependency closure.

Files Changed: Identity review/result contracts, correction domain, repository, API composition,
tests, Registry 1.9.0, ADR, Project State and this handoff.

Validation Performed: 9 targeted tests, Ruff, strict mypy and Registry generation; full gate runs at
the stage checkpoint.

Completed: H02 engineering implementation.

Not Completed: real reviewer usability, cross-series scale and real identity accuracy.

Risks / Blockers / Open Decisions: generic PostgreSQL dependency graph is authoritative; H06 must
exercise real transaction concurrency when legal fixtures are available.

Next Exact Step: implement H03 observable Fact and supporting/opposing Evidence fusion.

Project State Update: State Version 29.
