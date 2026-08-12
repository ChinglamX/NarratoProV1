# Handoff — G02 Benchmark Harness

Handoff ID: `H-2026-08-12-G02`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A / AI System Engineer

Objective: 建立 E06 Provider 的数据隔离、严重错误和可重放评测地基。
Active Epic / Backlog ID: E06 / G03
Starting State Version: 22

Inputs Read: Stage 2 Acceptance/Provider Benchmark、Calibration Program、G01 contracts。

Decisions Made: ADR-029；series-isolated split；Frozen Test 禁止 tuning；failure 显式；slice 与 severe error 独立；无真实标签不设门槛。

Files Changed: benchmark Contracts/Harness/Registry、synthetic corpus、acceptance script/tests、Catalog/ADR/State。

Validation Performed: `scripts/accept_g02.py`、full `make check`、Registry history/freshness、TypeScript。

Completed: G02 engineering corpus/harness and reproducible acceptance。

Not Completed: real annotated Speech/Visual corpus、production quality thresholds、Provider bake-off。

Workspace State: G02 ready to commit；runtime unchanged。

Risks / Blockers / Open Decisions: real dataset rights/annotation agreement remain G03/G04 work；synthetic fixture cannot support admission。

Next Exact Step: implement typed Speech Observation contracts and benchmarkable deterministic/local provider path through G01 Gateway。

Project State Update: State Version 23。
