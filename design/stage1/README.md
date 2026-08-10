# Stage 1 — Production Foundation

Version: 1.0

## 1. 目标

Stage 1 建设最终生产系统的稳定内核，使后续 AI、媒体和创作模块只实现标准 Worker/Artifact Contract，不再各自处理状态、版本、恢复和审核。

本阶段不实现剧情理解或成片质量算法，但其可靠性标准与最终生产环境一致。

---

## 2. 组件拓扑

```text
Review Workspace / API Client
            │
            ▼
        FastAPI API
            │ command/query
            ▼
      Temporal Workflow ───── signals/updates ─── Review API
            │
     ┌──────┼────────┐
     ▼      ▼        ▼
 CPU Worker AI Worker Render Worker
     │      │        │
     └──────┼────────┘
            ▼
 Artifact Registry / Dependency Graph
       │                    │
 PostgreSQL            Object Store
       │
 OpenTelemetry → Prometheus / Grafana / Logs
```

---

## 3. 设计文件

- `01_DATABASE_AND_ARTIFACTS.md`
- `02_WORKFLOW_AND_EXECUTION.md`
- `03_TIMELINE_AND_OTIO.md`
- `04_RESOURCE_AND_CONCURRENCY.md`
- `05_REVIEW_AND_CORRECTION_API.md`
- `06_OBSERVABILITY_AND_FAILURES.md`
- `07_ACCEPTANCE_AND_BUILD_ORDER.md`

---

## 4. 输入

- Project Command
- Source Asset URI 与 Rights Metadata
- Automation Policy
- Resource Profile
- Platform/Genre/Model Config refs

---

## 5. 输出

- 可迁移的数据库 Schema
- immutable Artifact Registry 与 Dependency Graph
- durable Project Workflow 和 Worker Contract
- Master Timeline Core 与 OTIO Adapter
- Resource Admission 与 Task Queue
- Review/Correction API
- traces、metrics、logs 和故障处理
- 可自动执行的 Stage 1 验收测试

---

## 6. 非目标

- 不选择最终 ASR/VLM/TTS 模型
- 不实现 Story/Strategy Agent
- 不构建完整 Timeline Editor UI
- 不生成正式营销成片
- 不启用 L2+ 自动审核

---

## 7. 强制原则

- PostgreSQL 是元数据事务真相源。
- Object Store 保存大 payload，正式 blob 不可变。
- Temporal 是 Workflow 状态真相源，数据库不复制其内部事件历史。
- Master Timeline 是编辑时间真相源。
- 所有正式写入依赖数据库约束保证幂等。
- Review/Correction 产生新版本，不覆盖原 artifact。
- 所有模型与工具通过 Worker/Provider Contract 接入。
