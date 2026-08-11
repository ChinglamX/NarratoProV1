# Handoff — E02 Artifact and Persistence Core

Handoff ID: `H-2026-08-12-E02`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A System Engineering / AI System Engineer

Objective: 完成可供 E03–E05 使用的 PostgreSQL transactional artifact core 和单机 Object Store。
Active Epic / Backlog ID: E03 / D01
Starting State Version: 16

Inputs Read:
- Stage 1 Database/Artifacts、Cross-cutting Production、Package Dependency、E02/C01–C05、ADR-001–023
- 当前 Contract Registry v1.2.0、Compose PostgreSQL 16 和工程工具链

Decisions Made:
- ADR-024：PostgreSQL 16 + SQLAlchemy Core + Alembic + psycopg；不可变 baseline migration。
- LocalObjectStore 为首个正式单机 adapter；S3-compatible 保持同一 Port/commit semantics。
- Artifact CAS、transactional outbox、dependency cycle/closure 和 publication pointer 均由数据库事务保护。

Files Changed:
- `packages/persistence/`：baseline/schema、database、Artifact/Blob/Command/Policy repositories。
- `packages/artifacts/object_store.py`：ObjectStore Port 与 Local adapter。
- `migrations/`、`alembic.ini`：revision 0001_e02。
- `scripts/accept_e02.py`：真实 PostgreSQL acceptance。
- `tests/artifacts/`、`tests/persistence/`：Object Store 和 schema tests。
- `pyproject.toml`：psycopg runtime dependency。

Validation Performed:
- Alembic upgrade→downgrade→upgrade：真实 PostgreSQL 隔离库通过。
- `accept_e02.py`：并发 CAS 1 winner、cycle rejected、closure=2、Artifact/Outbox=4/4、Blob commit、idempotency/publication conflicts、config/rights 通过。
- pg_dump/pg_restore：恢复库对账 Artifact=4、Outbox=4、Config=1、Rights=1。
- `make check`：105 passed，83.96% coverage；Ruff/mypy/Bandit/Context/Architecture/Schema 全通过。
- Review Web offline TypeScript typecheck：通过。

Completed:
- C01–C05 和 E02 退出能力。

Not Completed:
- E03 Temporal Workflow/Review/Resource/Observability。
- MinIO/S3 adapter；LocalObjectStore 已满足单机正式路径。

Workspace State:
- branch `master`；E02 commit 待创建。
- 隔离数据库 `narratopro_e02_acceptance`、`narratopro_e02_restore` 包含测试数据；未触碰主数据库。

Risks / Blockers / Open Decisions:
- Python resolution lock 未建立。
- S3-compatible adapter 在共享多机部署前必须实现和做故障测试。

Next Exact Step:
- E03/D01：实现 ProjectRunWorkflow skeleton、typed state/query/cancel/replay 和 Task Queue conventions。

Project State Update:
- `PROJECT_STATE.md` → State Version 17。
