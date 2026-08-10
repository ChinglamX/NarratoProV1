# Evaluation Plane Detailed Design

Version: 1.0

## 1. 目标

把质量审核、人工修正、置信度校准、实验和线上反馈连接为可验证闭环，同时防止系统用自评分自我批准。

---

## 2. 四层评价

### Contract & Technical QC

确定性检查：Schema、依赖、时长、编码、同步、响度、字幕边界、资产缺失和权利状态。

工具：Pydantic/JSON Schema、FFprobe/FFmpeg、OpenCV、音频测量、Rights Policy。

### Content Correctness

检查人物、事件、时间线、因果和解说是否与 Evidence 一致。

工具：规则、检索、独立 LLM/VLM reviewer、人工 gold labels。

### Creative Quality

检查 Hook、节奏、解说、画面、音频、字幕和整体传播表达。

工具：结构化 rubric、多 reviewer、pairwise comparison、demo benchmark、人工 Review Director。

### Online Performance

真实发布后的曝光、3 秒留存、平均观看、完播、跳出、互动与转化。

线上效果与离线质量分开存储，不能用播放数据合理化剧情错误或侵权。

---

## 3. Benchmark System

### Dataset

- demo reference 及人工时间线拆解
- 不同题材、长度、画质、方言和人物规模的项目样本
- 正常样本、边界样本和已知失败样本
- Story/Strategy/Timeline/Render 多层 gold 或人工 adjudication

### Versioning

每个 benchmark 记录 dataset_version、annotation guideline、reviewer、disagreement 和适用范围。

### Tooling

MLflow 可用于 Prompt/模型版本、评测运行、指标和 artifacts；关键项目元数据仍写入本系统 Artifact Registry。

---

## 4. Quality Review Pipeline

```text
Technical Precheck
→ Blocker Detection
→ Evidence-based Correctness
→ Creative Rubric Scoring
→ Cross-review / Disagreement
→ Human Release Package
```

每个问题包含 timecode/artifact、problem、evidence、severity、suggested fix、affected dependencies。

AI reviewer 与 generator 必须逻辑隔离：不同 Prompt，重要场景可使用不同模型或人工复核，避免同一错误被自洽地重复认可。

---

## 5. Confidence Calibration

### 数据

预测 score、method、scope、实际 correctness、correction type、risk class。

### 指标

- Brier Score / calibration error
- reliability diagram / Expected Calibration Error
- severe false negative rate
- review precision
- automation coverage
- correction rate

### 建设

1. L1 Shadow 收集。
2. 按模块/模型/类型分桶评测。
3. 拟合校准器或规则聚合。
4. 离线 replay。
5. L2 小范围灰度。
6. 漂移检测和自动降级。

模型自报概率不能跳过此过程。数据不足时 status=unavailable/shadow。

---

## 6. Human Correction Loop

Correction Record 必须表达：

- before/after
- semantic operation
- reason/taxonomy
- artifact/model/prompt/config
- reviewer and time
- downstream invalidation

分析任务：

- 哪些模块/类型错误率最高
- 高置信度错误集中在哪里
- 人工常改哪些 Timeline 操作
- 哪些 Prompt/Config 版本退化

输出只能是 Candidate Prompt/Config/Model/Policy version，必须经过评测、审批、灰度和回滚。

---

## 7. Automation Levels

### L1

全部 Gate 人工决定；建立基准和 Shadow Confidence。

### L2

低风险、已校准模块自动流转；blocker、unavailable、冲突转人工。

### L3

风险分层抽样：随机样本+高风险邻域+分布漂移样本。不是简单抽 10%。

### L4

反馈用于受控优化候选版本；不允许模型直接改生产配置。Release Gate 仍由人决定。

升级按模块进行，要求最小样本、类型覆盖、稳定窗口、严重漏检上限和回滚演练。

---

## 8. Online Experiment

### 前提

- 合法获取平台数据
- variant_id 与发布记录唯一关联
- 实验样本和时间窗口可解释
- 同期策略、受众、投放等混杂因素有记录

### 数据

- impression
- 3s retention
- average watch duration
- completion rate
- drop-off curve
- engagement/conversion

### 局限

- 平台分发不是随机实验，易有选择偏差。
- 小样本不应得出强结论。
- 高播放不等于适用于其他题材或账号。
- A/B 候选只有在发布与统计设计成立时才叫 A/B Experiment。

---

## 9. 并发

- Technical QC 按 Variant 并行。
- 时间片级 blocker scan 可并行，最终按成片聚合。
- 多 AI reviewer 可并行保留独立结果，不先互相污染。
- Benchmark replay 按样本并行并受模型预算限制。
- Calibration 与 experiment analysis 使用离线批处理，不阻塞生产主流程。

---

## 10. 生产验收

- Review 问题可定位并触发最小失效范围。
- 阻断项永远优先于总分和置信度。
- 同一 benchmark 可重放比较模型/Prompt/Config。
- 自动化升级有可复现报告和 rollback target。
- 高置信度严重错误触发自动降级。
- 线上指标来源、窗口和实验分组可审计。
- AI reviewer 无法自行批准 Release。
