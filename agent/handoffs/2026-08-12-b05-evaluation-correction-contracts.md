# Handoff — B05 Evaluation and Correction Contracts

Handoff ID: `H-2026-08-12-B05`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A System Engineering / AI System Engineer

Objective: 完成 E01/B05 的质量、修正、评估、校准、适用范围和自动路由基础契约。
Active Epic / Backlog ID: E02 / C01
Starting State Version: 14

Inputs Read:
- 项目强制 Tier 1 文件和实际 Git/runtime 状态
- `design/architecture/09_CORE_DATA_CONTRACTS.md`
- `design/stage6/01`–`05`
- `design/calibration/README.md`、`01_CALIBRATION_PROGRAM.md`
- E01/B05 Backlog、ADR-009/010/016/019/021 和现有 Contract Registry

Decisions Made:
- ADR-022 固定 S0/S3、unresolved/disagreement、Correction successor lineage、ApplicableScope 和 fail-closed routing 语义。
- Registry 兼容新增升级为 v1.1.0，v1.0.0 不修改。
- 保留 B02 `ConfidenceRecord.applicable_scope` 字符串以避免 v1 breaking change；结构化 scope 由新 Calibration/Routing contracts 使用。

Files Changed:
- `packages/contracts/evaluation.py`：七组 canonical contracts、枚举和校验不变量。
- `packages/contracts/__init__.py`、`registry.py`：公开导出并注册 v1.1.0。
- `generated/contracts/versions/1.1.0/`、latest 和 Review Web TS：跨语言生成物。
- `tests/contracts/test_evaluation.py`：严重度、歧义、版本 lineage、生命周期和安全路由测试。
- `design/implementation/09_ARCHITECTURE_DECISIONS.md`：ADR-022。

Validation Performed:
- `make check`：83 passed，87.68% coverage；Ruff、mypy、Bandit、Context、Architecture、Schema freshness 全通过。
- `apps/review_web/node_modules/.bin/tsc --noEmit -p apps/review_web/tsconfig.json`：通过。
- `git diff --check`：通过。
- Registry：52 schemas/components/types，70 artifact types；history compatibility 通过。

Completed:
- B05 代码、不可变 Registry v1.1.0、测试、ADR 和恢复点。
- E01 Canonical Contracts 完成。

Not Completed:
- C01 PostgreSQL/SQLAlchemy/Alembic database baseline。
- Routing policy execution engine、L2/L3 calibration activation 和任何生产自动放行。

Workspace State:
- branch `master`；B05 checkpoint 将随本次 commit 保存。
- `docker ps` 已确认七项 NarratoPro Compose 服务保持运行，PostgreSQL、Temporal 和 MinIO healthy；本轮未写 runtime 数据或执行外部发布。

Risks / Blockers / Open Decisions:
- Python resolution lock 尚未建立。
- C01 必须选择并记录首个 Object Store adapter，但不得与 database baseline 耦合。
- 真实 Calibration Pack/Gold 不存在，Automation 保持 L1/Shadow。

Next Exact Step:
- 按 C01 读取 E02 persistence 设计，冻结 SQLAlchemy/Alembic schema 和 PostgreSQL migration acceptance，再开始首个 migration。

Project State Update:
- `PROJECT_STATE.md` → State Version 15。
