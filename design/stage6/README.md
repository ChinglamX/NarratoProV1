# Stage 6 — Quality Automation and Feedback Intelligence

Version: 1.0

## 1. 目标

把历史 Run、Review、Correction、Benchmark 和合法线上数据连接成受控质量闭环：减少重复机械审核，同时保证高风险内容、创意判断和最终发布仍由人负责。

系统只能提出、评测和灰度 Prompt、Model、Config、Calibration 或 Automation Policy 候选，不能根据自身评分直接修改生产环境。

项目级数据集、Calibration Pack 和持续运营规范以 `design/calibration/README.md` 为统一入口；本阶段实现其评测、路由和发布基础设施。

---

## 2. 闭环拓扑

```text
Runs / Artifacts / Reviews / Corrections / Performance
                         │
             Quality Event Normalization
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
 Blocker Detectors  Confidence Labels  Feedback Dataset
       │                 │                 │
       └──────────── Benchmark / Calibration ──────────┐
                                                        ▼
                              Candidate Prompt/Model/Config/Policy
                                                        │
                                   Offline Eval → Approval → Canary
                                                        │
                                    Monitor → Promote / Rollback
                                                        │
                                                        ▼
                                       Versioned Production Policy
```

离线评测不阻塞正常生产；实时路由只读取已批准、版本化且未漂移的 Policy Snapshot。

---

## 3. 设计文件

- `01_QUALITY_EVENTS_AND_BLOCKER_DETECTORS.md`
- `02_CORRECTION_DATA_PIPELINE.md`
- `03_CONFIDENCE_CALIBRATION.md`
- `04_AUTOMATION_ROUTING_SAMPLING_AND_DRIFT.md`
- `05_EVALUATION_REGISTRY_AND_BENCHMARK.md`
- `06_CANDIDATE_RELEASE_AND_ROLLBACK.md`
- `07_ONLINE_PERFORMANCE_AND_EXPERIMENTS.md`
- `08_GOVERNANCE_OBSERVABILITY_AND_SECURITY.md`
- `09_ACCEPTANCE_AND_BUILD_ORDER.md`

---

## 4. 输入

- Stage 1–5 Run、Artifact、Trace、Cost 和 Rights records
- ReviewDecision、CorrectionRecord、问题时间码和 reviewer disagreement
- Versioned Benchmark/Evaluation Dataset
- Confidence Shadow predictions 与人工 correctness labels
- 合法 Release/Performance/Experiment data
- 当前 Prompt、Model、Config、Rubric、Automation Policy versions

---

## 5. 输出

- NormalizedQualityEvent、BlockerDetection、ReviewPackage
- CorrectionDataset、AnnotationQualityReport
- CalibrationReport、DriftReport
- Approved AutomationPolicyRef 与 RoutingDecision/Audit
- Candidate Prompt/Model/Config/Rubric/Threshold versions
- EvaluationComparison、RolloutPlan、RollbackTarget
- PerformanceComparison/ExperimentResult 与 ApplicableScope

---

## 6. 非目标

- 不自动批准 Release Gate。
- 不用 AI reviewer 自评分证明自身正确。
- 不用人工介入率作为自动化升级的唯一依据。
- 不让线上播放表现改写 Fact 或 Story。
- 不把观察性平台数据伪装成随机 A/B 实验。
- 不让反馈任务直接写生产 Prompt、配置或模型路由。
- 不以降低 blocker 召回率换取更高自动化覆盖。

---

## 7. 强制不变量

- Blocker 优先于总分、Confidence 和线上表现。
- Confidence 必须绑定 method、calibration version、scope、risk 和 evidence。
- 模型/Prompt/Config 改变超出校准适用范围时，Confidence 退回 shadow/drifted。
- Automation Level 按 module/task/scope 管理，模块级策略优先。
- unavailable、drift、conflict、rights 和严重风险默认 fail closed。
- 反馈只创建 Candidate；Production 发布必须审批、canary、监控、可回滚。
- Release Gate 在 L0–L4 都由人决定。

---

## 8. 阶段验收摘要

- Blocker detector 使用故障集验证严重漏检率，问题能定位到时间码/Artifact。
- Calibration 在独立测试集按模块/模型/类型评测，不跨任务复用分数含义。
- L2 路由、L3 风险抽样、漂移和自动降级均完成故障演练。
- Candidate → Eval → Approval → Canary → Promote/Rollback 全链路可追踪。
- Correction 数据有结构、版本、质量和隐私治理。
- 线上结果明确数据来源、样本、窗口、分组、混杂因素与适用范围。
- 系统可以证明自动化没有降低严重错误控制，而不是只证明人工变少。

完整构建与验收见 `09_ACCEPTANCE_AND_BUILD_ORDER.md`。
