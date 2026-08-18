# Project Canonical Index

Version: 1.0

## 1. 作用

本文件是项目自身的上下文导航和权威来源索引。它回答：项目是什么、去往何方、当前状态在哪里、某类决策应读取哪份文件。

它不记录频繁变化的进度；当前进度只写入 `PROJECT_STATE.md`。

---

## 2. 冷启动顺序

任何 Agent 或开发者开始任务时，按顺序读取：

1. `AGENTS.md`：行为、角色、强制规则。
2. `PROJECT_INDEX.md`：权威文件和任务路由。
3. `PROJECT_STATE.md`：当前阶段、完成项、下一步、风险。
4. `agent/CONTEXT_RECONSTRUCTION_PROTOCOL.md`：恢复与验证流程。
5. 当前任务所需的 Tier 1/Tier 2 文件。

在完成 Context Reconstruction Check 前不得修改代码、Schema、Roadmap 或核心设计。

---

## 3. 项目北极星

项目定位：个人可运行、可扩展、生产级的 AI 短剧营销视频系统。

输入：具有合法处理权限的单集或多集短剧资产。

输出：事实可追溯、策略可审核、时间线可编辑、质量可评价的营销候选；仅人工 Release Gate 通过后可发布。

目标质量：达到或超过项目 demo 的专业营销成片质量，但不以复制 demo 表面样式为目标。

核心链路：

```text
Media → Observation → Fact → Story → Strategy → Timeline
→ Voice/Audio/Subtitle/Render → Quality → Human Release
```

---

## 4. 权威来源层级

发生不一致时按以下优先级处理：

1. `PROJECT_CHARTER.md`：项目使命、产品边界和成功标准。
2. `PROJECT_RULES.md`：不可违反的全局原则。
3. `SYSTEM_ARCHITECTURE.md`：五域职责和真相源。
4. `PRODUCT_CAPABILITY.md`：产品能力边界。
5. `quality/QUALITY_STANDARD.md`：质量、blocker 和通过条件。
6. `workflow/PRODUCER_WORKFLOW.md`：三个正式 Gate 与生产流程。
7. `design/implementation/09_ARCHITECTURE_DECISIONS.md`：冻结实施决策。
8. `design/implementation/05_SCHEMA_AND_ARTIFACT_CATALOG.md`：Canonical 数据名称与所有者。
9. 对应 Stage/Implementation/Calibration 详细设计。
10. `PROJECT_STATE.md`：只决定当前进度和恢复点，不覆盖以上规范。

若低层文件与高层纲领冲突，停止实施，登记冲突并先修正文档。禁止自行选择更方便的版本。

---

## 5. 不可重新发明的核心决策

- 五个稳定域：Control、Intelligence、Strategy、Timeline Production、Evaluation。
- 六个生产能力阶段，不是低质量版本序列。
- 首个生产形态：模块化单体、多进程 Worker，不先微服务化。
- Temporal 是唯一耐久 Workflow；LangGraph 只在 AI Activity 内。
- PostgreSQL 是业务元数据真相源；Object Store 保存 blob。
- Master Timeline 是唯一编辑时间真相源。
- Artifact 不可变；修正和回滚创建后继版本或 pointer event。
- 正式 Gate 只有 Story、Strategy、Release；Release 永远人工。
- AI 输出带 Evidence/版本；Confidence 未校准时只能 shadow/unavailable。
- 反馈只产生 Candidate，不能自行修改生产配置。
- Provider 可替换；代码许可、模型权重和资产权利分别审计。

需要改变上述任一项，必须提交 ADR、影响、迁移、测试和回滚，不得在普通编码任务中隐式改变。

---

## 6. 权威文档路由

### 项目与治理

- 项目使命：`PROJECT_CHARTER.md`
- 产品能力：`PRODUCT_CAPABILITY.md`
- 产品控制看板：`PRODUCT_CONTROL_BOARD.md`
- 产品控制与模块成熟度：`product/PRODUCT_CONTROL_SYSTEM.md`
- 模块验证卡：`product/MODULE_VALIDATION_CARDS.md`
- 总体架构：`SYSTEM_ARCHITECTURE.md`
- 全局规则：`PROJECT_RULES.md`
- 路线图：`DEVELOPMENT_ROADMAP.md`
- 当前状态：`PROJECT_STATE.md`

### Agent

- Agent 操作系统：`AGENTS.md`
- 角色：`agent/AGENT_SYSTEM.md`、`agent/AGENT_ROLE.md`
- 上下文恢复：`agent/AGENT_CONTEXT.md`、`agent/CONTEXT_RECONSTRUCTION_PROTOCOL.md`
- 交接模板：`agent/HANDOFF_TEMPLATE.md`

### 工程与质量

- 工程规则：`engineering/DEVELOPMENT_RULES.md`
- 技术栈：`engineering/TECH_STACK.md`
- 质量标准：`quality/QUALITY_STANDARD.md`
- 审核协议：`quality/QUALITY_REVIEW_PROTOCOL.md`
- 生产流程：`workflow/PRODUCER_WORKFLOW.md`

### 架构与实施

- 总体详细设计：`design/architecture/README.md`
- Stage 1–6：`design/stage1/README.md` 至 `design/stage6/README.md`
- 实施蓝图：`design/implementation/README.md`
- Schema Catalog：`design/implementation/05_SCHEMA_AND_ARTIFACT_CATALOG.md`
- Epic 顺序：`design/implementation/07_EPICS_AND_DELIVERY_SEQUENCE.md`
- 首批 Backlog：`design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md`
- ADR：`design/implementation/09_ARCHITECTURE_DECISIONS.md`
- 上下文恢复工程规范：`design/implementation/10_CONTEXT_AND_RECOVERY.md`
- 校准计划：`design/calibration/README.md`

### 证据与验证（2026-08-16 起）

- 差距评估：`evaluation/reports/PROJECT_GAP_ASSESSMENT.md`
- E06 视觉 benchmark v1/enriched：`evaluation/benchmarks/e06_visual_v1(_enriched).json`
- E06 容量并发 probe：`scripts/probe_e06_capacity.py` → `evaluation/reports/E06_CAPACITY_RESULTS.md`
- E06 容量验收计划：`evaluation/reports/E06_CAPACITY_ACCEPTANCE_PLAN.md`
- E06 admission 升级评估：`evaluation/reports/E06_ADMISSION_UPGRADE_ASSESSMENT.md`
- E07 Story 推理真实数据验收：`scripts/accept_e07_story_real_data.py`
- E10/K02 take selection：`packages/production/take_selection.py`
- E10/K05 字幕碰撞：`packages/production/subtitle_collision.py`
- E10 TTS adapter：`packages/providers/speech/indextts.py`（IndexTTS 运维见 `PROJECT_STATE.md` §7 恢复信息）

---

## 7. 按任务加载

### TYPE A — System Engineering

必读：项目/Agent/工程/质量 Tier 1，随后读取 Implementation Blueprint、ADR、Schema Catalog、当前 Epic 和相关 Stage 文件。

### TYPE B — Drama Production

必读：Project Charter、Product Capability、Quality Standard、Producer Workflow、当前 Project/Run/Artifact/Story/Strategy/Timeline refs。不得默认加载全部工程设计。

### TYPE C — Quality Review

必读：Quality Standard、Review Protocol、Producer Workflow、目标 Artifact lineage、Benchmark/Profile 和对应 Stage Acceptance。

### 产品进度、范围或工具效果审查

必读：`PRODUCT_CONTROL_BOARD.md`、`product/PRODUCT_CONTROL_SYSTEM.md`、`product/MODULE_VALIDATION_CARDS.md`；先回答 First Usable Cut 的可见产物和 blocker，再查看 Epic 工程状态。

### 修改核心契约或架构

额外必读：Architecture Review、Package Dependency、Schema Catalog、Workflow Map、ADR；先给出兼容和迁移影响。

### 接入 Provider

额外必读：Technology Matrix、Stage 2/5 Provider 规格、Calibration Program、Rights Policy 和 Resource Profile。

---

## 8. 项目状态更新规则

`PROJECT_STATE.md` 只记录：

- 当前有效阶段/Epic/任务；
- 已完成并验证的能力；
- 进行中与下一项；
- 阻断、风险和未决决策；
- 最近验证命令/结果；
- 最新交接摘要和权威引用。

完成重要任务后必须更新。计划或对话中的“已完成”不能替代状态文件证据。

状态更新不得复制大段设计；只使用稳定 ID、结论和链接。

---

## 9. 完整性检查

项目 CI 最终必须检查：

- README、AGENTS、INDEX、STATE 和恢复协议存在且非空。
- INDEX 中引用文件存在。
- STATE 中 active Epic/Task 存在于 Epic/Backlog。
- Canonical Contract/ADR 无未登记替代名。
- 完成状态有测试/评测/审核证据。
- 核心文档变更要求同步状态或明确 `state_impact: none`。
