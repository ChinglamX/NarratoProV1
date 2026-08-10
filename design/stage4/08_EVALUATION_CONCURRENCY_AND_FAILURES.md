# Evaluation, Concurrency and Failures

Version: 1.0

## 1. 目标

建立 Stage 4 的分层质量评测、资源并发、成本追踪、失败恢复和反馈采集，使创意时间线既可规模化计算，也不因自动化牺牲观看质量。

输入：Stage 4 Workflows、Evaluation/Benchmark Dataset、Resource Profile、Timeline Reviews/Corrections。

输出：Stage4Benchmark、QualityReport、Capacity/Cost Report、FailureReport、CorrectionDataset、OptimizationCandidate。

---

## 2. Task Queue

| Queue | 工作 | 约束 |
|---|---|---|
| timeline_cpu | compiler、validator、patch/diff、solver | CPU、project commit |
| retrieval | DB/vector/candidate features | DB/query/IO |
| vision_geometry | crop/optical-flow/composition | CPU/GPU/Metal、memory |
| creative_model | rhythm/narration/VLM suggestions | model/token/context |
| preview_render | proxy preview | encoder、CPU、disk、thermal |
| timeline_eval | benchmark、full-sequence checks | candidate-set barrier |

不同 Variant 并行；同一 Timeline commit 串行。Shot/Crop/Beat/Draft 可 fan-out，序列连续性、全文解说和全局节奏在汇合点执行。

---

## 3. Resource Admission

Activity 声明 CPU、RAM、VRAM/Metal、disk、encoder session、token/cost、预计输出大小和时间。Admission Controller 同时考虑：

- 模型驻留和 batch；
- FFmpeg/OpenCV 与模型争用统一内存；
- preview render 的磁盘与温度压力；
- Project fairness 和交互 Review 优先级；
- Candidate/Revision/Preview Budget。

交互式局部 preview 可获得有限优先级，但不能饿死持久化正式任务。

---

## 4. 分层评测

确定性正确性：Timeline invariants、source/timeline range、evidence refs、constraint、crop bounds、dependency invalidation、preview parity。

算法质量：retrieval recall/precision、continuity issue detection、subject coverage、CropPath stability、duration estimate、narration fact/redundancy。

创意质量：Hook bridge、叙事清晰、节奏张弛、镜头价值、解说口语/细腻/画面价值，由人工完整观看并记录时间码。

不得把上述三类合成一个掩盖 blocker 的总分。LLM-as-judge 可作问题召回，不能单独批准 Timeline。

---

## 5. 故障与恢复

- Planner/Provider 失败：对应 Proposal unavailable，其他模块可继续，Compiler 不假装完整。
- Solver timeout：返回 best-known、gap/未满足约束和可重试策略。
- Preview render 失败：Timeline 不回滚、不设为无效；typed error 可重试。
- OOM：降低 batch/分辨率后有限重试，再隔离输入并建议 fallback。
- 磁盘高水位：停止新 preview，清理无引用 staging/cache，不删除正式 artifact。
- stale Story/Brief/Profile：阻止 Timeline commit 或 approval。
- Worker crash：使用 Stage 1 heartbeat/idempotency 恢复。

---

## 6. 可观测性

Trace：Brief → Beat → Retrieval/Planner → Proposal → Compiler/Reflow → Timeline → Preview → Review。

Metrics：

- Timeline/preview wall time、queue wait、cache hit；
- candidate pool、solver iterations/timeouts/conflicts；
- crop feasibility/fallback/manual rate；
- duration conflict、reflow scope/rounds；
- narration blocker/rewrite/lock rate；
- preview failure、peak memory/disk/encoder utilization；
- human edit density、time-to-approve、Proposal accept/reject；
- demo benchmark gaps 按维度。

高基数 ID 进入 trace/log，不作为 Prometheus label。

---

## 7. 反馈与自动化

记录人工 clip replace、trim、crop keyframe、Beat move、Narration rewrite、lock、Proposal accept/reject 和原因，关联 Timeline/Brief/Story/Model/Prompt/Profile。

反馈只生成 retrieval weight、Profile、Prompt、solver/rubric 候选版本，必须 benchmark、审批、canary 和可回滚发布。人工编辑不能直接训练并上线。

可高度自动化：Timeline validation、source/evidence checks、crop bounds、依赖失效、preview 生成。长期人工主导：镜头停留、关键节奏、解说语体和复杂构图取舍。

---

## 8. 性能测试

覆盖长 Story、多 Beat、多 Variant、高密度人脸/字幕、复杂 CropPath、大量局部 Preview 和并发 Review。报告 P50/P95、吞吐、峰值内存/磁盘、solver 时间、模型 token/cost 和每个 ApprovedTimelineIntent 人工耗时。

Mac mini 建立首个 Resource Profile；硬件差异必须形成独立容量报告，不能照搬并发数。

---

## 9. 测试与验收

- 并发 fan-out、backpressure、worker kill、OOM、磁盘高水位和 solver timeout。
- 硬 blocker 永不因 Planner/Critic 高分通过。
- Preview 失败不损坏或错误批准 Timeline。
- Correction 只影响声明范围，人工 lock 不丢失。
- 所有创意质量结论有完整观看和问题时间码。
- 历史 Timeline 可用原 Profile/Prompt/Compiler version 重放。
