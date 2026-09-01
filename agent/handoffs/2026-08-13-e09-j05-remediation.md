# Handoff Record — E09/J05 精确多轨编辑审计修复

Handoff ID: 2026-08-13-e09-j05-remediation
Date / Author: 2026-08-13 / Kun (AI System Engineer, TYPE A)
Task Type / Active Role: System Engineering Task / AI System Engineer

Objective:
- 审查豆包提交 `367066b`（J05 precise multi-track editing）及其未提交改动，修复发现的工程缺口，使 `make check` 全绿且符合仓库规范（不可变迁移、沙箱细粒度、L1 fail-closed）。

Active Epic / Backlog ID: E09 / J05 Precise Multi-track Editing
Starting State Version: 47 → Ending: 48

Inputs Read:
- PROJECT_STATE.md v47、ADR-047/048/049、08_INITIAL_IMPLEMENTATION_BACKLOG.md（J05 DoD）
- `367066b` 全量 diff、未提交 3 文件 diff、timeline_editing/timeline_repository/timelines API/review_repository/validator/real_preview/creative_activities/baseline_v0001/media_schema 源码
- 测试基建：tests/apps/test_timeline_api.py、test_timeline_editing_service.py、test_real_preview.py、tests/persistence/conftest 模式

Decisions Made:
- ADR-050（design/implementation/09_ARCHITECTURE_DECISIONS.md，用户确认）：approved-intent 编辑锁定、append-only 版本分配、局部预览端点、沙箱细粒度 passthrough、迁移不可变。
- 用户授权（request_user_input）：丢弃豆包未提交的迁移改写与 worker 全局沙箱改动，按规范重做。

Files Changed:
- packages/persistence/media_schema.py：media 表独立 MetaData，不再污染 baseline snapshot（迁移全新库失败根因）。
- apps/worker/main.py：恢复（撤销全局 SandboxedWorkflowRunner passthrough）。
- migrations/versions/0001_e02_baseline.py、0002_e05_media_identity.py：恢复为已提交版本（不可变迁移）。
- workflows/media/__init__.py、workflows/visual/__init__.py：细粒度 imports_passed_through（scenedetect/cv2/numpy C 扩展沙箱重复加载）。
- packages/persistence/timeline_repository.py：commit 改 max(version)+1 append-only；新增 approved_intent_version()。
- apps/services/timeline_editing.py：apply_patch 加 approved-intent 门禁；undo/redo/jump/get_version 存储冲突统一包装；新增 get_version()。
- apps/api/timelines.py：/patches 内联路径加门禁；JumpRequest.version ge=1；新增 POST /{id}/preview-partial + _resolve_source_paths。
- packages/production/real_preview.py：`.mp4.part` → `.tmp.mp4`（ffmpeg 容器推断 bug）；assert → raise（Bandit B101）。
- tests/foundation/test_settings.py：显式 bootstrap URL（本地 .env 干扰修复）。
- tests/persistence/test_database_schema.py：baseline 不被 media 污染回归测试。
- tests/apps/test_timeline_api.py：FakeRepository 扩展 + 10 个新端点测试。
- tests/apps/test_timeline_editing_service.py：fake 支持 approved；新增 TestApprovedIntentGate 2 测试。
- tests/production/test_partial_preview.py：新增（changed_ranges 4 + 渲染 2）。
- tests/persistence/test_timeline_repository_db.py：新增（真实 Postgres 4 测试，CI 无 DB 跳过）。
- PROJECT_STATE.md（v48）、design/implementation/09_ARCHITECTURE_DECISIONS.md（ADR-050）。

Validation Performed:
- `make check`：全绿 — 352 passed / 4 skipped（DB 测试需 NARRATOPRO_DATABASE_URL）、80.61% coverage、Ruff、strict mypy（176 files）、Bandit、Context/Architecture、Registry 2.18.0 freshness/history。
- 迁移：真实 Postgres 全新库 `alembic upgrade head` 成功（0001→0002），downgrade base→upgrade head 往返成功；media.ingest_identity 存在。
- DB 回归：`narratopro_test` 库 4/4 通过（undo→新编辑 v4 追加、pointer CAS、approved_intent_version 往返）。
- Worker：`python -m apps.worker.main` 无沙箱全局放开，7 个 workflow 全部通过沙箱验证并持续运行（手动停止 exit 0）。
- 局部预览集成测试：真实 ffmpeg 渲染 0.5s 片段 + ASS sidecar 成功。

Completed:
- 豆包未提交改动（worker 沙箱、迁移改写）按授权丢弃；根因修复（media_schema 解耦）替代。
- 编辑通道 L1 approved-intent 锁定（服务 + /patches 双路径）。
- undo→新编辑版本分配修复 + 真实 DB 回归测试。
- 局部预览端点接线 + ffmpeg 扩展名 bug 修复 + 测试。
- 沙箱细粒度 passthrough，worker 真实启动验证。
- State v48、ADR-050、settings/迁移测试确定性。

Not Completed:
- `/patches` 与 TimelineEditingService 双实现合并（审查器拒绝大改；bounded debt，行为一致）。
- `packages/timeline/revisions.py`（RevisionHistory）删除（审查器拒绝；bounded debt，需人工批准）。
- Review Web 尚未调用版本列表/diff/局部预览 API。
- CI 无 Postgres service（DB 测试在 CI 跳过）；建议后续加 service。
- E09 四个真实退出 blocker 未解决；`engineering_complete=false` 不变。

Workspace State:
- 分支 master；工作区含本轮未提交修改（大量文件）；HEAD 仍为 `1139694`（367066b 已在其上）。
- 本地 Postgres/Temporal/MinIO 等容器运行；`narratopro_test` 隔离库已建并迁移（可复用跑 DB 测试）。
- 本地 `.env`（gitignored）存在，settings 测试已不受其影响。

Risks / Blockers / Open Decisions:
- 审查器（agent reviewer）对删除/委托式重构/文档中段插入敏感；大改动需用户确认或小步提交。
- 沙箱修复只覆盖 media/visual 两个包；未来新 workflow 若引入其他 C 扩展依赖链，需按同一模式处理（禁止全局 passthrough）。
- 版本 append-only 后，undo 分支的旧版本成为孤儿审计行（有意保留，文档已注明）。

Next Exact Step:
- 提交本轮全部修改（建议单 commit，message 参照 `feat(E09/J05): audit-remediate precise editing`）。
- 之后按 PROJECT_STATE.md §4：用真实 Approved Story/Creative Brief/Media 执行 candidate-to-demo 全片人工审核、Worker restart/replay、Timeline checkpoint 正式认证（E09 退出证据）。
