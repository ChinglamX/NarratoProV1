# Handoff — B01 Foundation Contracts

Handoff ID: `H-2026-08-11-B01`
Date / Author: 2026-08-11 / Codex
Task Type / Active Role: TYPE A System Engineering / AI System Engineer

Objective: 实现 E01/B01 的跨域基础值对象、规范序列化与性质测试。
Active Epic / Backlog ID: E01 / B02
Starting State Version: 10

Inputs Read:
- `PROJECT_INDEX.md` v1.0、`PROJECT_STATE.md` v10、`agent/CONTEXT_RECONSTRUCTION_PROTOCOL.md` v1.0
- `design/architecture/09_CORE_DATA_CONTRACTS.md` v1.0
- `design/implementation/04_API_AND_COMMAND_MODEL.md` v1.0
- `design/implementation/05_SCHEMA_AND_ARTIFACT_CATALOG.md` v1.0
- `design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md` v1.0

Decisions Made:
- UUIDv4、exact rational time、字符串 checksum 和 canonical JSON 固定在 ADR-018。
- 公共 Contract 共享 immutable/forbid-extra base；B02 只能引用 B01 类型。
- Hypothesis 是 property test 的开发依赖，不进入运行依赖。

Files Changed:
- `packages/contracts/base.py`：公共严格模型和 canonical serialization。
- `packages/contracts/foundation.py`：B01 六组基础值对象与边界。
- `packages/contracts/calibration.py`、`packages/contracts/__init__.py`：复用公共 base 并导出唯一类型。
- `tests/contracts/test_foundation.py`：边界、round-trip 和 property tests。
- `pyproject.toml`：Hypothesis dev dependency。
- `design/implementation/09_ARCHITECTURE_DECISIONS.md`：ADR-018。

Validation Performed:
- `make check`：32 passed，93.26% coverage；Ruff、strict mypy、Bandit、Context/Architecture checks 成功。
- `docker compose --env-file deploy/compose/.env.example -f deploy/compose/docker-compose.yml ps`：七服务保持 Up，三个带 health 服务 healthy。

Completed:
- B01 代码、测试、ADR 和项目恢复状态。

Not Completed:
- B02 Evidence/Confidence/Rights contracts。
- Python resolution lock 决策。

Workspace State:
- branch `master`；B01 checkpoint 将随本次 commit 保存。
- NarratoPro 七项 Compose 服务及四个 named volume 保持运行；未写 runtime 数据。

Risks / Blockers / Open Decisions:
- ProviderIdentity 当前保存单个 license snapshot 字符串；B02 RightsMetadata 承担结构化权利语义，禁止在 B01 扩出第二套 rights 模型。
- Python 环境尚无 resolution lock；R1 退出前必须完成。

Next Exact Step:
- 按 B02 实现 EvidenceLink、ConfidenceRecord、RightsMetadata/Manifest refs，并先冻结 unavailable/shadow 与 unknown-rights 的 fail-closed 不变量。

Project State Update:
- `PROJECT_STATE.md` → State Version 11。
