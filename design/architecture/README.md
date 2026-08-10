# Production Architecture Detailed Design

Version: 1.0

## 1. 设计目标

本设计把 SYSTEM_ARCHITECTURE.md 的五个架构域拆解为可建设、可并发、可验证的生产系统。

目标不是罗列模型，而是明确：

- 模块为什么存在
- 使用什么开源工具以及为什么
- 如何建设和替换
- 输入、输出与数据所有权
- 并发、资源隔离、幂等和失败恢复
- AI 可以自动化什么，不能可靠自动化什么
- 每一阶段达到什么可观测效果

---

## 2. 总体技术原则

### 双层编排

- Temporal：负责跨小时/天的耐久工作流、重试、超时、暂停、恢复和人工 Gate。
- LangGraph：仅用于 Story、Strategy、Review 等需要有状态推理和工具循环的 AI 子流程。
- FFmpeg、ASR、VLM、TTS 等重计算作为 Temporal Activity 或独立 Worker 执行，不在 Agent 进程内长时间运行。

### 三类真相源

- PostgreSQL：项目、版本、依赖、审核、配置和索引元数据的事务真相源。
- Object Storage：原片、中间媒体、模型输出、音频和成片的二进制真相源；本地部署使用文件系统适配器，扩展时切换 S3-compatible 实现。
- Master Timeline：成片编辑关系的唯一时间真相源；内部使用强类型 Schema，并提供 OpenTimelineIO 导入导出适配器。

### AI 与确定性系统分离

- AI 负责候选、推理、排序和建议。
- 确定性系统负责约束、状态、版本、校验、渲染、同步和发布阻断。
- AI 输出必须保留 Evidence、Confidence、模型、Prompt 和配置版本。

---

## 3. 五域文档

- `01_CONTROL_PLANE.md`
- `02_INTELLIGENCE_PLANE.md`
- `03_STRATEGY_PLANE.md`
- `04_TIMELINE_PRODUCTION_PLANE.md`
- `05_EVALUATION_PLANE.md`
- `06_CROSS_CUTTING_PRODUCTION.md`
- `07_IMPLEMENTATION_STAGES.md`
- `08_TECHNOLOGY_MATRIX.md`
- `09_CORE_DATA_CONTRACTS.md`

Stage 1 可编码规格入口：`design/stage1/README.md`。

Stage 2 可编码规格入口：`design/stage2/README.md`。

Stage 3 可编码规格入口：`design/stage3/README.md`。

Stage 4 可编码规格入口：`design/stage4/README.md`。

Stage 5 可编码规格入口：`design/stage5/README.md`。

Stage 6 可编码规格入口：`design/stage6/README.md`。

跨阶段工程实施蓝图入口：`design/implementation/README.md`。

贯穿建设与生产运行的校准计划入口：`design/calibration/README.md`。

---

## 4. 端到端数据流

```text
Project Command
  → Durable Workflow
  → Media Catalog + Rights
  → Parallel Fact Extraction
  → Evidence-backed Story Graph
  → Strategy + Hook Candidates
  → Approved Creative Brief
  → Master Timeline Draft
  ↔ Visual / Rhythm / Narration Iteration
  → TTS Alignment + Audio + Subtitle
  → Render Candidates
  → Offline Quality + Human Review
  → Release-approved Artifact
  → Optional Performance Feedback
```

---

## 5. 并发层级

1. Project 并发：不同短剧项目完全隔离。
2. Episode 并发：多集视频可并行探测和提取事实。
3. Segment 并发：Scene/Shot/Audio Chunk 可并行推理。
4. Model Worker 并发：按 CPU、GPU、Apple Silicon 和云端配额分别限流。
5. Variant 并发：批准 Story 后，多策略和多成片版本可并行。
6. Track 并发：TTS、字幕准备、BGM 搜索可并行；最终 Timeline Conform 后汇合。

所有并发都必须受 Resource Profile、Cost Budget 和 backpressure 控制，不能把“支持并发”理解为无限并行。

---

## 6. 生产完成标准

- 任一结果可追踪到完整依赖链。
- 工作进程崩溃后不会丢失任务或重复提交正式产物。
- 上游局部修改只失效受影响的下游。
- 模型替换不破坏数据契约。
- 人工可以在 Story、Strategy、Timeline 和 Release 阶段精确修改。
- 自动化升级由校准数据决定，阻断项和发布决策不被置信度覆盖。
