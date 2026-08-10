# Provider Benchmark and Confidence

Version: 1.0

## 1. 目标

建立模型/工具准入、对照、回退、质量分层和 Confidence Shadow 机制。不存在仅凭公开榜单或单个 demo 进入生产的 Provider。

输入：Versioned Evaluation Dataset、Provider Package、Resource Profile、Quality Profile。

输出：BenchmarkRun、SliceMetrics、ErrorCases、CalibrationReport、ProviderApproval、RoutingPolicyCandidate。

---

## 2. Provider Package

每个 Provider 必须声明：

- capability、implementation/version、model checksum；
- code license、weight license、commercial scope；
- supported hardware、precision/quantization、memory estimate；
- input limits、language/domain scope、data residency；
- deterministic controls、raw response schema；
- timeout、retry safety、batch behavior；
- fallback compatibility 与 known limitations。

缺少权重来源、许可证或 checksum 的模型只能进入 research policy，不能进入 production routing。

---

## 3. Evaluation Dataset

数据集按项目真实失败模式分层，至少包含：

- 视频：硬切、叠化、闪光、黑场、快速运动、暗光；
- ASR：普通话、方言、BGM、喊叫、重叠、专名、否定和数字；
- OCR：烧录字幕、艺术字、竖排、手机、文件、运动模糊；
- Identity：正侧脸、遮挡、换装、多人相似、跨集、双胞胎；
- Story：倒叙、梦境、说谎、身份揭示、隐含因果、缺失片段。

Split 按剧/系列隔离，禁止同剧相邻片段同时进入训练/调参与最终测试。所有标注记录 guideline version、annotator、agreement 和 unresolved label。

---

## 4. 指标体系

| 能力 | 核心指标 | 必须单列的严重错误 |
|---|---|---|
| Scene/Shot | boundary precision/recall、tolerance F1 | 漏掉剧情切换、过度切碎 |
| ASR | CER、entity CER、timestamp deviation | 人名、否定、金额/时间反转 |
| Diarization | DER/JER、speaker count error | 关键对白归错人物 |
| OCR | text recall/precision、track accuracy | 关键文件/手机内容错读 |
| Detection/Tracking | mAP/recall、IDF1/HOTA 类指标 | 关键人物漏检、轨迹串人 |
| Identity | pair/cluster precision-recall | 错误 merge 高于错误 split 风险 |
| Story | event precision/recall、evidence entailment、causal accuracy | 身份、时间、因果、结局错误 |

总体平均值不能掩盖关键 slice。准入规则按能力和风险分别配置。

---

## 5. Confidence 设计

ConfidenceRecord 的 method 可以来自校准后的模型分数、ensemble consistency、evidence coverage、规则约束和质量特征。LLM 自报概率只能作为 supporting factor。

流程：

1. Stage 2 初期所有分数为 `shadow`，不控制正式路由。
2. 在冻结测试集和人工审核数据上拟合/选择校准器。
3. 评估 reliability curve、ECE/Brier、selective risk 和 severe false negative。
4. 声明 calibration_version、applicable_scope 和过期条件。
5. 只有达到 Automation Policy 的模块可从 shadow 变为 calibrated。
6. 数据漂移、Provider/Prompt/Config 变化超出适用范围时标记 drifted 并退回 L1。

不同任务的 0.8 不具有相同含义，禁止跨 ASR、Identity、Story 共用阈值。

---

## 6. Bake-off 与路由

Provider 评测同时比较：质量、严重错误、P50/P95、吞吐、峰值内存、冷启动、失败率、成本、数据政策和许可证。

Routing Policy 优先满足 blocker/rights/data residency，再在已准入 Provider 中按 Quality Profile 和 Resource Profile 选择。回退必须兼容输出 Contract，但不要求数值完全一致。

每次升级采用 shadow → canary → staged rollout。新 Provider 产生独立 artifact；发现回归时回切 routing config，不覆盖已生成结果。

---

## 7. 回归与漂移

- 固定 golden set 进入 CI 的轻量结构/关键案例测试。
- 完整 benchmark 在 Provider、模型、Prompt、依赖或硬件变化时运行。
- 生产抽样记录 slice 分布、人工修正率、高置信错误和 unavailable rate。
- 分布漂移只触发告警/降级和重评，不自动重训练上线。

Benchmark Report 必须关联代码 revision、container/model digest、dataset version、配置、硬件和原始预测 artifact。

---

## 8. 验收

- 至少一个主 Provider 和一个明确的 unavailable/manual 路径；回退模型不是强制，但回退语义必须存在。
- 每个能力有分层数据集、严重错误 taxonomy 和准入门槛。
- 未校准分数不能改变 Story Gate 路由。
- Provider 替换无需修改业务 Contract。
- 许可证或数据政策失败能在运行前阻断。
- Benchmark 完整可复现，并能定位每个错误到输入和模型版本。

