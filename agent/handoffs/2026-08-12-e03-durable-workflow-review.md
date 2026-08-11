# Handoff — E03 Durable Workflow and Review

Handoff ID: `H-2026-08-12-E03`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A System Engineering / AI System Engineer

Objective: 完成 E03 的 durable orchestration、Command/Review/Correction、资源准入、可观测性和 Shadow instrumentation。
Active Epic / Backlog ID: E04 / E01 Master Timeline Domain
Starting State Version: 17

Inputs Read:
- Stage 1 Workflow/Resource/Review/Observability、E03/D01–D07、ADR-001–024。
- E02 PostgreSQL schema/repositories、Temporal 1.25 runtime 和现有 Contract Registry。

Decisions Made:
- ADR-025：Temporal history 只保留小型 pointer/state；外部 I/O 仅 Activity。
- Command/Review/Correction 均 DB-first + transactional outbox；Signal 可重复并由 workflow 去重。
- Release 仅 human release_approver；Automation 继续 L1，Confidence/Correction 仅 Shadow。
- Resource Admission 使用可过期 lease，未知/超预算 fail closed；metrics label 固定低基数。

Files Changed:
- `workflows/project/`、`apps/worker/main.py`：durable workflow/activity/typed state。
- `apps/api/`：Project/Run Command、Review Decision、Correction preview/apply。
- `packages/control/`、`packages/persistence/`：review/correction/outbox/resource/reconciler adapters。
- `packages/observability/`、`packages/evaluation/shadow.py`：trace/redaction/metrics/shadow example。
- `scripts/accept_e03*.py`、对应 tests。

Validation Performed:
- `make check`：126 tests、coverage gate、Ruff/mypy/Bandit/Context/Architecture/Registry 全通过。
- 真实 Temporal：retry、wait、Worker restart、duplicate Signal、history replay、non-retryable 通过。
- 真实 PostgreSQL/API：Command idempotency、Run outbox、Correction CAS、Review first-wins、Release RBAC 通过。

Completed:
- D01–D07 与 E03 exit evidence。

Not Completed:
- E04 Master Timeline 实现；生产常驻 outbox dispatcher/dashboard UI 将随部署与 Review Workspace 增强。
- 任何 L2/L3 routing。

Workspace State:
- E03 修改已验证，阶段 commit 待创建。
- 验收向隔离 `narratopro_e02_acceptance` 增加 E03 测试数据；主数据库未触碰。

Risks / Blockers / Open Decisions:
- Python resolution lock 仍未建立。
- Temporal workflow 后续变更必须用保存 history 做 replay regression。

Next Exact Step:
- E04/E01：实现 Master Timeline domain、RationalTime invariants、canonical serialization 和 golden fixtures。

Project State Update:
- `PROJECT_STATE.md` → State Version 18。
