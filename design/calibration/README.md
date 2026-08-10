# Calibration Program

Version: 1.0

## 1. 目标

将系统校准作为贯穿 Stage 1–6 的持续建设流，而不是代码完成后的临时调参。所有 Provider、Prompt、Config、Detector 和 Automation Policy 必须用真实项目数据证明适用范围、质量和风险。

---

## 2. 设计文件

- `01_CALIBRATION_PROGRAM.md`：校准对象、数据、指标、阈值和发布流程
- `02_CALIBRATION_PACK_V1.md`：首个真实项目校准包的建设规格
- `03_OPERATING_CADENCE.md`：持续校准、漂移、降级和治理节奏

---

## 3. 输入

- Stage 1–5 的 Artifact、Run、Review、Correction、Trace 和 Cost
- Stage 2–5 Provider/Prompt/Config 的 Shadow 输出
- 人工 Story、Strategy、Timeline、Voice/Audio/Subtitle 和 Release 决策
- demo benchmark 与代表性真实短剧
- 合法线上 Performance/Experiment 数据（可选）

---

## 4. 输出

- Versioned Calibration Pack
- Development/Validation/Frozen Test manifests
- Annotation Guideline 与 Error Taxonomy
- Module Baseline、CalibrationReport、ApplicableScope
- Threshold/AutomationPolicy Candidate
- Candidate/Champion Evaluation 与 RollbackTarget
- 持续 Drift/Correction/Automation Safety Report

---

## 5. 强制原则

- 校准按模块/任务/模型/类型/语言/平台分别进行。
- Accuracy、Craft Quality、Online Performance 和 Confidence 分开评价。
- 先满足严重漏检限制，再提高 Automation Coverage。
- 同一剧/系列不得跨 train/dev/test 泄漏。
- Frozen Test 不用于反复调 Prompt 或阈值。
- 无足够真实标签时保持 L1/Shadow。
- 每次 Model/Prompt/Config 变化都检查旧 Calibration 是否仍适用。
- Release 永远由人决定。

---

## 6. 阶段关系

```text
Stage 1: 契约、版本、Review/Correction、Trace
Stage 2: 感知/Story Shadow 与人工 gold
Stage 3: 候选选择、pairwise preference、Strategy correction
Stage 4: Timeline edit density、完整观看、demo benchmark
Stage 5: Voice/Audio/Subtitle/Render 故障集与媒体 QC
Stage 6: Calibration、Routing、Sampling、Drift、Candidate rollout
```

Stage 6 负责校准平台和自动化发布，但校准数据从 Stage 1 起采集，不能等到最后才补。

---

## 7. 测试与验收

- 每个上线 Provider/Prompt/Config 有对应 benchmark 或明确 research 状态。
- 每个自动路由模块有 CalibrationRef、scope、阈值、严重错误数据和 rollback。
- 每次人工修正可以进入结构化 Correction Dataset。
- 能回答“系统在哪些范围可靠、哪些范围必须人工”。
- 能重放 Candidate 与 Champion，并证明晋级没有降低 blocker 控制。
