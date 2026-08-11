# Handoff — E04 Master Timeline Core

Handoff ID: `H-2026-08-12-E04`
Date / Author: 2026-08-12 / Codex
Task Type / Active Role: TYPE A System Engineering / AI System Engineer

Objective: 完成唯一 Master Timeline 的领域、并发、OTIO、Preview Compiler/Workflow 和真实验收。
Active Epic / Backlog ID: E05 / F01 Ingest Registration and Rights Snapshot
Starting State Version: 18

Inputs Read:
- Stage 1 Timeline/OTIO、E04/E01–E05、Canonical Timeline Contract、ADR-005/006/011/023/025。
- OpenTimelineIO 官方 0.18.1 文档/PyPI、宿主 FFmpeg/FFprobe 8.1.2。

Decisions Made:
- ADR-026：内部 MasterTimeline 唯一真相；OTIO 仅交换并强制 LossReport。
- Patch 以 Timeline active pointer + item version 两级乐观并发；disjoint 可 rebase，same-item 冲突。
- RenderPlan deterministic；Foundation Preview 固定 FFmpeg 8.1.2，并明确 ASS sidecar 非 burn-in。

Files Changed:
- `packages/timeline/`：validator、patch/diff/rebase、OTIO adapter、compiler。
- `packages/persistence/timeline_repository.py`、`apps/api/timelines.py`：Timeline successor/CAS API。
- `packages/production/fake_preview.py`、`workflows/timeline/`：Preview/QC/Artifact durable workflow。
- `scripts/accept_e04.py`、timeline/production/workflow tests。
- `pyproject.toml`：OpenTimelineIO 0.18.1 exact dependency。

Validation Performed:
- `make check`：143 tests、80.06% coverage、全部工程/安全/上下文/Registry gate 通过。
- Review Web 本地 TypeScript 5.9.3 typecheck 通过。
- 真实 PostgreSQL/Temporal/FFmpeg：semantic rebase/conflict、OTIO、Preview/QC、Artifact lineage、human checkpoint 通过。

Completed:
- E04/E01–E05 和 R1 Foundation 退出能力。

Not Completed:
- E05 Media Ingest；Fake Preview 不代表真实素材 ingest 或 demo 成片质量。
- ASS burn-in；宿主 FFmpeg 8.1.2 无 libass filter，已显式保留 sidecar。

Workspace State:
- E04 修改已验证，阶段 commit 待创建。
- 隔离验收数据库增加 E04 Project/Run/Timeline/Preview 数据；主数据库未触碰。

Risks / Blockers / Open Decisions:
- Python resolution lock 未建立；OTIO 已 exact pin 但未形成全依赖 lock。
- E05 必须验证 VFR/rotation/corrupt/multi-audio 和 FFmpeg codec coverage。

Next Exact Step:
- E05/F01：实现 source identity、rights snapshot、duplicate/import policy 和可恢复 ingest command。

Project State Update:
- `PROJECT_STATE.md` → State Version 19。
