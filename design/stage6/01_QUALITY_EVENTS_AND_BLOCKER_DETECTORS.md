# Quality Events and Blocker Detectors

Version: 1.0

## 1. 目标

统一 Stage 1–5 的技术、事实、创意、权利和自动化安全问题表达，并建设可定位、可评测、可降级的 Blocker Detector pipeline。

输入：Artifact/Timeline/Render、Evidence、Technical QC、Review Rubric、Rights/Platform/Quality Profile。

输出：NormalizedQualityEvent、BlockerDetectionSet、DetectorCoverageReport、ReviewRoutingHint。

---

## 2. Quality Event Contract

每个事件包含：event_id、module/dimension、issue_type、severity、blocker、target ArtifactRef、time/frame/source range、evidence/raw metric、detector identity、ConfidenceRecord、Profile rule、suggested fix、status 和 reviewer label。

状态：detected、confirmed、dismissed、corrected、superseded、unresolved。Detector 输出不能直接改生产 artifact。

Taxonomy 分层：contract/technical、rights、story correctness、marketing/hook、rhythm、narration、visual、audio、subtitle、automation safety。

---

## 3. Detector 类型

### Deterministic

Schema、checksum、引用、时长、编码、同步边界、响度/peak、字幕越界/缺字、rights state、stale version。适合高自动化，但仍需故障集验证实现正确性。

### Statistical/ML

黑帧/冻结、语音可懂度风险、遮挡、内容重复、异常节奏、事实蕴含候选。必须输出 uncertainty/scope，不能默认成为 blocker 真相。

### AI Reviewer

剧情、Hook、解说、连续性和创意问题召回。使用独立 Prompt/Provider 和 Evidence retrieval；结果默认建议或转人工，不自行 Release。

### Human

Review Director 的确认、驳回和新增问题是 adjudicated label 的主要来源，但仍保存 reviewer disagreement。

---

## 4. 检测流水线

```text
Required Check Resolution
→ Deterministic Precheck
→ Time-window Detector Fan-out
→ Evidence-based Reviewer
→ Dedup / Merge / Severity Resolution
→ Missing/Unavailable Check Scan
→ Review Package
```

Required checks 由 artifact type、stage、Platform/Quality/Automation Policy 决定。检测器未运行或 unavailable 不能等价于“没有问题”。

---

## 5. 合并与优先级

同一问题按 target/time/taxonomy/evidence 聚类，保留所有 detector 原始结果。Severity 合并使用版本化规则；人类确认和确定性硬规则优先，但人工豁免不能覆盖 rights、文件损坏等不可豁免 blocker。

不同 detector 分歧输出 Disagreement，不简单平均 Confidence。一个高分 Pass detector 不能抵消另一个已确认 blocker。

---

## 6. 并发与成本

Variant、时间窗口和 detector 并行；全片 duration/loudness/continuity 与 issue dedup 在汇合点执行。先运行低成本 deterministic checks，再根据结果与风险调度高成本 AI reviewer。

每个 detector 有 timeout、resource/cost budget、required/optional 和 fallback。Required detector unavailable 时按 Policy fail closed。

---

## 7. 评测

每类 detector 在正常、边界和故障注入样本上报告 precision、recall、severe false negative、定位误差、unavailable、latency 和成本。

Blocker detector 选择阈值优先控制严重漏检，再评估 Review Precision 和 Automation Coverage；不能只优化总体 F1。

人工 gold 包含 guideline/version、reviewer、adjudication 和 unresolved，不把单个 reviewer 当绝对真相。

---

## 8. 测试与验收

- 每类 Quality Standard blocker 有固定正负故障样本。
- Detector crash/unavailable 不产生假 Pass。
- 时间分块边界问题不漏检或重复计数。
- Dedup 保留不同证据和 detector disagreement。
- 问题可从 Review Workspace 跳转到精确 timecode/artifact。
- 确认问题能路由到最小 Correction/失效范围。

