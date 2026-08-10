# Workflow and Deployment Map

Version: 1.0

## 1. 目标

把六阶段 Use Case 映射到 Temporal Workflow、Activity、Task Queue、Worker 进程和部署环境，同时保持 Workflow history 精简、可重放和资源安全。

输入：Stage 1–6 workflow/concurrency 设计、Repository/Package rules。

输出：Workflow Hierarchy、Activity Rules、Task Queue Map、Worker/Deployment Topology。

---

## 2. Workflow 层次

```text
ProjectRunWorkflow
├── FoundationValidation
├── IntelligenceWorkflow
│   ├── EpisodeIntelligenceWorkflow[*]
│   └── StoryAssemblyWorkflow
├── StrategyWorkflow
├── TimelineWorkflow
│   └── VariantTimelineWorkflow[*]
├── ProductionWorkflow
│   └── VariantProductionWorkflow[*]
└── EvaluationWorkflow
    ├── ReleaseQualityWorkflow
    └── OfflineLearningWorkflow (separate/background)
```

ProjectRun 可以按目标 stage range 启动。Approval wait 位于 Story/Strategy/Release；内部 Checkpoint 使用 ReviewRequest/Signal，但不改变正式 Gate 数量。

---

## 3. Activity 规则

Activity 是 application use case adapter：输入只含小型 IDs/ArtifactRefs/config refs，输出 ArtifactRefs/summary，不把媒体、完整模型响应或大型 Timeline 放进 history。

每个 Activity 声明 execution_key、timeout、retry policy、heartbeat、cancellation、ResourceRequest、idempotency 和 typed errors。

外部 I/O、随机、当前时间、FFmpeg 和模型调用只在 Activity。Workflow 使用确定性排序、版本 marker 和 Continue-as-new。

---

## 4. Task Queue Map

| Queue | Worker Capability | 典型 Activities |
|---|---|---|
| control | low-resource orchestration adapters | DB command projection/reconcile |
| media_cpu | FFprobe/FFmpeg/OpenCV | ingest/proxy/extract/mix/QC |
| audio_ml | ASR/alignment/TTS | speech/voice |
| vision_ml | OCR/detection/tracking/embedding | perception/crop features |
| vlm_local | local VLM | bounded visual reasoning |
| cloud_model | external LLM/VLM/TTS | strategy/story/critic providers |
| graph_cpu | identity/fact/story graph | fusion/assembly |
| timeline_cpu | compiler/solver/diff | patch/reflow/validation |
| preview_render | interactive proxy | partial/full preview |
| final_render | final FFmpeg | candidate render |
| evaluation | benchmark/calibration/dataset | offline quality/learning |

Queue 名称稳定，具体 worker 能力通过 Resource Profile/Build ID 区分，不把机器地址写入 workflow。

---

## 5. Fan-out 与汇合

- Episode/Shot/AudioSegment/Frame batch/Variant/Candidate 可 fan-out。
- Fan-out 分页，使用 Child Workflow 或批次，避免 history 爆炸。
- Identity global commit、Story assembly、Candidate diversity、Timeline compile、Conform、Mix/Render/QC 是明确汇合点。
- 汇合检查输入 snapshot 完整；失败 shard 不从集合静默消失。
- 长 history 通过 Continue-as-new，只携带 refs/summary/policy。

---

## 6. Review/Signal

Workflow 创建 ReviewRequest 后等待 Signal/Update。Decision 先事务提交数据库/outbox，再发送 Signal；Reconciler 修复丢失投递。

重复、乱序和 stale Decision 按 request/target version 幂等拒绝。Workflow Query 只返回状态摘要，不替代业务 read model。

Release Signal 必须验证人工 actor、Rights/QC/Quality refs 和无 blocker。

---

## 7. Worker Versioning

每次部署关联 git revision、container digest、Contract/Schema、Temporal Build ID、Provider/Profile compatibility。新 Workflow canary 到新 Build ID，存量 execution 保持兼容路由。

CI replay 冻结 history corpus。Workflow breaking change 使用 patch/version marker；旧分支在兼容窗口内保留。

---

## 8. 环境拓扑

Local development：PostgreSQL、Temporal、Object Store adapter、OTel/Prometheus/Grafana 通过 Compose；媒体/ML worker 可在宿主机运行以访问 Metal/VideoToolbox。

Single-machine production：服务数据与 cache/tmp 分盘/目录，worker 受 admission，数据库/对象备份，secrets 独立。

Multi-machine：共享 S3-compatible Object Store；API/worker 横向扩展；PostgreSQL/Temporal 按生产 HA 运维。无需改变 domain/contracts。

---

## 9. 故障与测试

- Worker kill、heartbeat resume、Activity timeout/retry/cancel。
- Signal 丢失/重复/乱序、DB/Workflow projection reconcile。
- Fan-out partial failure 和 snapshot completeness。
- Continue-as-new/Child cancellation/Build ID routing/replay。
- Resource queue backpressure、OOM/disk/rate/cost。
- 相同 command/activity 重试不重复提交或计费。

验收：从 API Command 到 Artifact/Review/Final/Quality 的 trace 完整，任一进程重启后无需人工修数据库。

