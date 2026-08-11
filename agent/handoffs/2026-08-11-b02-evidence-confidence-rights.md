# Handoff — B02 Evidence, Confidence and Rights

Handoff ID: `H-2026-08-11-B02`
Date / Author: 2026-08-11 / Codex
Task Type / Active Role: TYPE A System Engineering / AI System Engineer

Objective: 实现 E01/B02 的 Evidence、Confidence 和 Rights 公共契约及 fail-closed 边界。
Active Epic / Backlog ID: E01 / B03
Starting State Version: 11

Inputs Read:
- 项目/Agent/质量/工程 Tier 1 全部必读文件
- `design/architecture/09_CORE_DATA_CONTRACTS.md` v1.0
- `design/implementation/03_PACKAGE_DEPENDENCY_RULES.md` v1.0
- `design/implementation/05_SCHEMA_AND_ARTIFACT_CATALOG.md` v1.0
- `design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md` v1.0
- Stage 2 Confidence、Stage 5 Rights/QC、Stage 6 Routing 设计

Decisions Made:
- ADR-019 固定 Confidence/Rights fail-closed 和显式时间点评估语义。
- Artifact-level Evidence 允许只引用 source；时间/帧/摘录按证据粒度选用，不虚构定位。
- B05 前 applicable_scope 保持非空字符串；B02 不提前定义第二套 ApplicableScope。

Files Changed:
- `packages/contracts/evidence.py`：Evidence、FrameRange、Confidence、Factor、Status、Risk。
- `packages/contracts/rights.py`：Rights metadata、typed grant/manifest refs、deterministic release blockers。
- `packages/contracts/__init__.py`：唯一公共导出。
- `tests/contracts/test_evidence_rights.py`：状态、score、scope、期限、授权和 unknown rights 边界。
- `design/implementation/09_ARCHITECTURE_DECISIONS.md`：ADR-019。

Validation Performed:
- `make check`：51 passed，92.43% coverage；Ruff、strict mypy、Bandit、Context/Architecture checks 成功。
- `.venv/bin/pytest tests/contracts -q`：32 passed。

Completed:
- B02 代码、测试、ADR 和状态恢复点。

Not Completed:
- B03 Command/Event/Error Envelopes。
- RightsGrant/RightsManifest payload、B05 ApplicableScope、任何自动路由。

Workspace State:
- branch `master`；B02 checkpoint 将随本次 commit 保存。
- 本任务无数据库 migration、runtime 数据写入或外部发布。

Risks / Blockers / Open Decisions:
- rights restrictions 当前保守转人工，后续 Policy/Rule Schema 必须显式解释后才可自动判定。
- Python resolution lock 仍未建立。

Next Exact Step:
- 按 B03 冻结 Command/Event/Error Envelope 的公共字段、稳定错误码和 redaction 边界，避免混入 B04 Schema Registry。

Project State Update:
- `PROJECT_STATE.md` → State Version 12。
