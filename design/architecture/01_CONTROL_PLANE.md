# Control Plane Detailed Design

Version: 1.0

## 1. 目标

Control Plane 保证所有长时间媒体任务可恢复、可审计、可限流、可人工暂停，不负责具体内容推理。

---

## 2. 模块设计

| 模块 | 建议工具 | 建设方式 | 输入 | 输出 | 并发 |
|---|---|---|---|---|---|
| API / Command | FastAPI + Pydantic | REST/事件接口，所有命令带 idempotency_key | 用户命令、配置 | Command Record、workflow_id | 多请求异步；数据库事务限流 |
| Durable Workflow | Temporal Python SDK | 每个 Project Run 一个 Workflow；Stage 为 Activity/Child Workflow | Command、ArtifactRef | 状态、重试、Signal、Result | 多 Workflow；按 Task Queue 隔离资源 |
| AI State Graph | LangGraph | 只嵌入 Story/Strategy/Review Activity；使用 checkpoint 和 interrupt | Typed AI State | 推理候选、待人工问题 | 节点可并行，模型调用受配额限制 |
| Metadata Store | PostgreSQL | 规范化核心表 + JSONB 扩展；乐观锁和唯一约束 | State mutation | 事务状态、版本、依赖 | 连接池；短事务；禁止长媒体事务 |
| Artifact Registry | PostgreSQL + Object Storage | 元数据与 blob 分离；内容寻址 checksum | Artifact payload/blob | immutable Artifact Version | 并行写临时对象，原子注册正式版本 |
| Policy Engine | 自研 typed rules；可选 OPA | 解析 Automation/Resource/Rights/Quality Policy | project/module context | effective policy、routing decision | 无状态横向扩展 |
| Review Gateway | Web UI + Temporal Signal/Update | 展示证据差异，提交结构化 Decision/Correction | awaiting_review artifact | Review Decision、new artifact version | 多 reviewer；目标版本乐观锁 |
| Scheduler / Quota | Temporal Task Queue + Resource Manager | CPU/GPU/MLX/API 分队列，token bucket 和 semaphore | Activity request | admission / queued / rejected | 按资源池配置并发上限 |

---

## 3. 为什么选择 Temporal + LangGraph

Temporal 用于确定性耐久执行：进程、网络或机器失败后恢复 Workflow；适合等待数小时的人工审核和长媒体任务。

LangGraph 用于 AI 内部状态、条件分支、工具调用和 interrupt。它不能替代媒体 Worker 的资源调度，也不应成为所有确定性 Pipeline 的唯一编排器。

边界：

```text
Temporal Workflow
  ├─ FactExtraction Activity
  ├─ StoryAgent Activity (internal LangGraph)
  ├─ Wait Story Signal
  ├─ StrategyAgent Activity (internal LangGraph)
  ├─ Media Activities
  └─ Wait Release Signal
```

---

## 4. 状态机

Run 状态：

```text
Created → Validating → Running → AwaitingReview
                  ↘ FailedRetryable → Running
                  ↘ FailedTerminal
AwaitingReview → Running / Rejected / Cancelled
Running → Succeeded
Succeeded → Superseded（输入版本变化时）
```

Artifact 状态与 Workflow 状态分离。Run 失败不删除已成功的 immutable artifacts。

---

## 5. 幂等与恢复

- 每个 Activity 使用 `(activity_type, input_checksums, config_versions)` 生成 execution_key。
- 重试前查询相同 execution_key 的完整结果；存在则复用。
- 外部模型/API 调用保存 request_id；不确定是否成功时先 reconcile，禁止盲目重复计费。
- FFmpeg 输出先写临时对象，探测和 checksum 通过后原子注册。
- 长任务按 Scene/Chunk 产生 checkpoint；Temporal heartbeat 只保存游标，不保存大 payload。

---

## 6. 并发与 Backpressure

建议资源队列：

- `cpu-media`：probe、demux、轻量 FFmpeg
- `cpu-ml`：OCR、轻模型
- `gpu-vision`：VLM、检测、Embedding
- `gpu-audio`：ASR、TTS、对齐
- `cloud-model`：商业 LLM/VLM API
- `render`：编码与合成

每个 Worker 声明 capacity。Scheduler 同时检查内存、GPU/MLX 占用、磁盘临时空间、云端 RPM/TPM 和预算。

并发策略：

- 不同 Project 优先公平调度。
- 同一 Project 的 Episode 可并行。
- 同一模型实例优先微批处理，而不是启动多个模型副本耗尽内存。
- Render 默认低并发，避免与本地模型争用统一内存带宽。

---

## 7. AI 自动化

可自动：

- 重试、缓存复用、资源路由、确定性校验
- 基于已校准 Policy 的低风险审核路由
- 自动生成差异和建议修复范围

不可自动保证：

- 创意方向正确
- 置信度天然可靠
- Release 合法或适合发布

Control Plane 只能执行 Policy，不能让模型临时改写 Policy。

---

## 8. 验收

- Worker 强制终止后 Workflow 可恢复。
- 同一 idempotency_key 重复提交只产生一个正式 Run。
- Review 等待超过进程生命周期仍可恢复。
- 上游 artifact 修订能计算准确失效集合。
- 资源不足时任务排队而不是 OOM。
- 每个状态变化都有审计记录和 trace_id。
