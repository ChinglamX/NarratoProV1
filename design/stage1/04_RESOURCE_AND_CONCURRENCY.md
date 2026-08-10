# Stage 1 Resource and Concurrency Design

Version: 1.0

## 1. 目标

让并发由资源预算和队列控制，而不是由调用方随意启动任务，避免 Mac 统一内存、GPU、磁盘或云端配额被耗尽。

---

## 2. Resource Profile

```yaml
profile_id: string
version: string
host:
  cpu_cores: integer
  memory_bytes: integer
  gpu_type: string | null
  gpu_memory_bytes: integer | null
  unified_memory: boolean
storage:
  temp_bytes_limit: integer
  low_watermark_bytes: integer
queues:
  cpu_media: integer
  cpu_ml: integer
  vision: integer
  audio: integer
  render: integer
cloud:
  rpm: integer
  tpm: integer
  max_cost_per_run: number
```

运行时保存 effective snapshot，不能读取会变化的 latest。

---

## 3. Activity Resource Requirement

```yaml
capabilities: [ffmpeg, metal, cuda, model:qwen-vl]
cpu_cores: number
memory_bytes: integer
gpu_memory_bytes: integer | null
temp_bytes: integer
exclusive_keys: [string]
estimated_duration_s: integer
cost_estimate: object
```

Scheduler 在 Activity 入队前做静态 admission；Worker 执行前再做动态水位检查。

---

## 4. Task Queue

- `cpu-media`：probe、demux、轻 FFmpeg。
- `cpu-ml`：轻量 OCR/特征。
- `vision-local`：本地 VLM/detection。
- `audio-local`：ASR/TTS/alignment。
- `cloud-model`：外部 API。
- `render`：高负载编码。
- `maintenance`：sweeper、reconciler、migration verify。

Task Queue 表示能力和隔离，不代表固定机器。

---

## 5. Admission 与 Semaphore

两级控制：

1. Workflow 层：预算、项目公平性、任务优先级。
2. Worker 层：进程 semaphore、模型实例 semaphore、磁盘/内存水位。

Apple Silicon 使用统一内存时，CPU memory 与 GPU memory 不能重复预算；模型驻留和 render 必须共享全局水位控制。

---

## 6. 调度公平性

- 默认 project round-robin。
- Interactive preview 高于 batch benchmark，但设置配额防止饿死。
- 同项目大量 Episode/Variant 设置 in-flight 上限。
- 维护任务有最低保留容量。
- priority 变更记录 audit，不允许用户无限抢占。

---

## 7. Micro-batching

适用：Embedding、OCR、VLM frames、ASR segments。

Batcher 按 provider/model/config/input shape 分组，达到 max_batch 或 max_wait_ms 触发。

每个输入仍有独立 activity/execution_key；batch failure 要能拆分定位，不能让一个坏样本永久阻塞整批。

---

## 8. Backpressure 与熔断

触发：

- queue_wait 超阈值
- memory/disk 达高水位
- API rate limit/error spike
- model OOM
- render temperature/throughput 退化

动作：

- 暂停 admission
- 降低 batch/concurrency
- 路由备选 provider/worker
- 延后低优先级任务
- 超预算 fail closed 或请求人工批准

---

## 9. 并发安全

- 同 Artifact version commit 使用 CAS。
- 同 Timeline Patch 使用 optimistic lock。
- 同 Project invalidation 使用 scoped lock。
- Provider cache key 包含模型、配置和输入 checksum。
- 不用进程内锁保证跨 Worker 正确性。

---

## 10. 容量基准

对每类 Activity 建立：

- cold/warm startup
- throughput per video minute
- P50/P95 duration
- peak memory/temp disk
- batch efficiency
- failure/OOM threshold
- local/cloud cost

Resource Profile 的默认并发来自实测，不来自 CPU 核数猜测。

---

## 11. 测试

- 超水位不启动新任务。
- 单项目不能占满所有队列。
- OOM 后降并发并成功重试或明确失败。
- micro-batch 中单坏样本可隔离。
- 云端 rate limit 遵守 Retry-After。
- Render 与本地模型并发不会突破统一内存预算。
