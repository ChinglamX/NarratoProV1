# Handoff — B03 Command, Event and Error Envelopes

Handoff ID: `H-2026-08-11-B03`
Date / Author: 2026-08-11 / Codex
Task Type / Active Role: TYPE A System Engineering / AI System Engineer

Objective: 实现 E01/B03 的 Command/Event/Error 公共 Envelope、稳定身份和公共错误脱敏边界。
Active Epic / Backlog ID: E01 / B04
Starting State Version: 12

Inputs Read:
- 项目/Agent/质量/工程 Tier 1 全部必读文件
- `design/implementation/04_API_AND_COMMAND_MODEL.md` v1.0
- `design/implementation/05_SCHEMA_AND_ARTIFACT_CATALOG.md` v1.0
- `design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md` v1.0
- `design/implementation/09_ARCHITECTURE_DECISIONS.md` ADR-001–019

Decisions Made:
- ADR-020 固定 UTC、三段 SemVer、JSON-only payload、idempotency/event identity 和 W3C trace ID。
- 内部 Error 与 Public Error DTO 分离；只有显式 public 且无 arbitrary data 的 detail 可投影。
- B03 仅维护字段形状快照；B04 必须吸收它并建立唯一 Schema Registry。

Files Changed:
- `packages/contracts/envelopes.py`：Command/Event/Error/PublicError 及兼容形状。
- `packages/contracts/__init__.py`：公共唯一导出。
- `tests/contracts/test_envelopes.py`：round-trip、UTC、trace、JSON payload、redaction 和 snapshot 测试。
- `tests/contracts/snapshots/b03_public_contract_shape.json`：B03 临时兼容快照。
- `design/implementation/09_ARCHITECTURE_DECISIONS.md`：ADR-020。

Validation Performed:
- `make check`：62 passed，93.86% coverage；Ruff、strict mypy、Bandit、Context/Architecture checks 成功。
- Envelope 模块 coverage 100%；B03 tests 11 passed。

Completed:
- B03 代码、测试、ADR 和状态恢复点。

Not Completed:
- B04 Schema Registry、JSON Schema/OpenAPI/TS generation、Artifact Type Registry。
- Command persistence/idempotency DB 行为；这些属于后续 Control/Persistence Epic。

Workspace State:
- branch `master`；B03 checkpoint 将随本次 commit 保存。
- 本任务无 migration、runtime 数据写入或外部发布。

Risks / Blockers / Open Decisions:
- Public message/remediation 依赖调用方提供审核过的稳定文本；不得转发 provider raw error。
- Python resolution lock 仍未建立。

Next Exact Step:
- B04 建立单一 Schema Registry，注册当前所有公共 Contract 与 Catalog Artifact Type，并将 B03 shape snapshot 纳入统一 breaking-change 检查。

Project State Update:
- `PROJECT_STATE.md` → State Version 13。
