# Resource, Incremental Computation and Review

Version: 1.0

## 1. 目标

让多集、多 Provider 感知和 Story 推理在个人机器或多 Worker 环境中安全并发，并支持局部修正、缓存复用、故障恢复和人工审核。

输入：Stage 2 Activity Graph、Resource Profile、Artifact Dependency Graph、Automation Policy、Review/Correction commands。

输出：AdmissionDecision、Queue/Reservation State、RecomputePlan、ReviewPackage、Correction Artifact、Capacity/Cost Report、Operational Metrics。

---

## 2. Task Queue 与汇合点

| Queue | 工作 | 并发约束 |
|---|---|---|
| media_cpu | probe、proxy、frame/audio extraction | CPU、磁盘、encoder session |
| audio_ml | VAD、ASR、alignment、speaker embedding | 模型驻留、音频 batch |
| vision_ml | OCR、detector、embedding | GPU/Metal 内存、分辨率 bucket |
| vlm_local | 本地 VLM | 单实例显存、上下文和 batch |
| cloud_model | 云端 VLM/LLM | rate、token、预算、数据政策 |
| fusion_cpu | identity/fact graph | Project commit lock、内存 |
| story_model | event/causal/arc | snapshot、context、预算 |

汇合点：Episode perception complete、Episode identity local complete、Project identity commit、Fact snapshot、global Story assembly、Story Review。

Temporal fan-out 必须分页/分批启动，避免一次写入海量 history；长批次使用 Child Workflow 和 Continue-as-new。

---

## 3. Admission 与容量模型

Activity 在排队前提交 ResourceRequest：CPU、RAM、VRAM/Metal、temporary disk、estimated duration、cloud cost 和 model residency key。

Admission Controller 检查：

- Resource Profile 上限和当前 reservation；
- 磁盘 low/high watermark；
- 模型互斥/共享驻留；
- Project fairness 和优先级；
- 云端预算、速率与数据出境；
- 下游 queue/backlog 和 Object Store 写入压力。

无法安全执行则保持 queued/backpressure；禁止先启动再依靠 OOM 重试。估算误差进入 Resource Observation，持续校准但不自动放宽硬上限。

---

## 4. 缓存键与增量失效

缓存键必须包含输入 checksum、Contract version、Provider/model checksum、配置/Prompt 版本和会改变结果的硬件/precision 参数。

典型失效规则：

- Source checksum 变化：全部派生结果 stale。
- Proxy Profile 变化：依赖代理数值的观察重算；源 Catalog 不变。
- FrameSamplePlan 变化：只重算新增/移除采样及其融合依赖。
- ASR hotword 变化：相关 transcript、speaker/fact/story 失效，不重跑视觉。
- OCR Provider 变化：OCR observation 及依赖事实失效。
- Character merge/split：受影响身份、Event participant、state/relationship/causal/arc 失效。
- Story Prompt 变化：Story 层重算，不重跑感知与 Fact。
- 人工 Fact Correction：只传播显式 dependency closure。

失效只改变状态并创建 RecomputePlan，不删除 artifact。

---

## 5. Review Workspace

### Identity Review

展示人物图库、Episode/Shot 分布、face/appearance/speaker evidence、cannot-link、冲突和 merge/split 影响。

### Fact Review

展示视频定位、ASR/OCR/视觉 observation、supporting/opposing evidence、人工文本/实体修正和下游影响。

### Story Review

展示事件线、人物状态、关系、因果和 Arc，支持编辑、接受、拒绝、unresolved 与补采请求。

所有修改通过 Stage 1 Correction API、optimistic concurrency 和 RBAC。Review UI 不直接写数据库内部表。

---

## 6. 自动化边界

Stage 2 默认 L1：AI 可以排序冲突、建议合并和生成 Review Package，但 Story Approval 必须人工决定。Confidence 以 shadow 记录。

未来 L2 也只允许经过校准的低风险感知/融合结果自动流转；身份反转、关键 Event、严重冲突、unavailable 和 blocker 必须进入人工。Release Gate 永远不在本阶段自动化。

人工介入率不是质量目标。系统优化优先减少重复机械确认，同时保证严重漏检率和 Evidence coverage。

---

## 7. 故障与降级

- 单 Episode/Provider 失败不丢失其他成功 artifact，可重跑失败 shard。
- Provider 不可用时标记 unavailable，可选择准入回退或人工补录。
- OOM 先缩 batch，再有限重试，之后隔离输入；不能无限退避占队列。
- Identity/Story commit 冲突重新读取最新 snapshot，不 last-write-wins。
- 云端预算耗尽停止新调用，已有本地结果继续汇合并产生 incomplete report。
- Reconciler 修复 artifact/workflow 投影，不替代 Story 决策。

---

## 8. 可观测性

Trace：Project → Episode Child Workflow → Provider Activity → Artifact → Fusion/Story → Review。

核心 Metrics：

- media minutes processed / wall hour；
- queue wait、model utilization、batch fill、peak memory；
- provider failure/fallback/unavailable；
- per-minute compute/cloud cost；
- Evidence coverage、conflict rate、Correction rate；
- Story review latency、stale/recompute fanout；
- Confidence calibration 和 severe false negative（有标注后）。

高基数 project/artifact 只进入 trace/log，不作为 Prometheus label。

---

## 9. 测试

- 多 Episode burst 下 admission、backpressure 与公平性。
- Worker kill、模型进程崩溃、磁盘水位、云端限流和预算耗尽。
- 相同输入并发执行只提交一个正式 artifact version。
- Correction 后实际失效集合与 expected dependency closure 一致。
- Review Signal 丢失/重复/乱序可 reconcile。
- 单机 Resource Profile 建立吞吐、峰值内存、磁盘和成本基线。
