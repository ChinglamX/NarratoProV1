# Handoff — G01 Provider Gateway

Handoff ID: `H-2026-08-12-G01`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: 建立 E06 所有 Speech/Visual Provider 共用的准入、调用和 raw response 边界。
Active Epic / Backlog ID: E06 / G02
Starting State Version: 21

Inputs Read: Stage 2 Speech/Visual/Provider Benchmark/Resource 设计、Schema Catalog、ADR、工程与质量规则。

Decisions Made: ADR-028；Provider adapter 不创建 Artifact；Gateway fail closed；raw response 独立 Artifact；typed normalized payload 延至 capability owner。

Files Changed: provider Contracts/Registry/Gateway/application service/tests、Schema Catalog、ADR/State/generated schemas。

Validation Performed: full `make check`；Registry history/freshness；Review Web TypeScript；定向 21 tests。

Completed: G01 Contract、implementation、raw persistence boundary 和 tests。

Not Completed: G02 corpus；任何真实 Speech/Visual Provider；ASR/OCR/Detection 质量声明。

Workspace State: G01 ready to commit；runtime/external services unchanged。

Risks / Blockers / Open Decisions: concrete provider versions/licenses and Mac mini benchmark must be resolved with official evidence in G02–G04。

Next Exact Step: implement G02 dataset/taxonomy/benchmark contracts and deterministic harness with series-leakage prevention。

Project State Update: State Version 22。
