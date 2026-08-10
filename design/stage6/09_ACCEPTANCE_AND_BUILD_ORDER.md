# Stage 6 Acceptance and Build Order

Version: 1.0

## 1. 目标与契约

目标：规定质量自动化与反馈闭环的依赖顺序、模块级升级标准、安全演练、数据治理、回滚和最终生产签收。

输入：Stage 1–5 生产数据、Stage 6 设计、Benchmark/Correction/Performance datasets、Quality/Automation/Security Policy 和测试环境。

输出：Milestone Evidence、Stage6 Acceptance Report、Approved Module Policies、Calibration/Drift Reports、Governance/DR Evidence、Rollback Records。

---

## 2. 构建顺序

### Milestone 1 — Quality and Correction Contracts

- QualityEvent、BlockerDetection、Correction taxonomy
- Dataset/Annotation/Performance schemas
- lineage、privacy/rights/retention rules

退出：Schema、taxonomy migration、数据拆分、权限和删除测试通过。

### Milestone 2 — Blocker Detection

- required check resolver、detector interface
- deterministic/ML/AI reviewer pipeline
- dedup/disagreement、Review routing

退出：Quality Standard blocker 故障集、定位、unavailable fail closed 和严重漏检 baseline 通过。

### Milestone 3 — Correction Dataset

- normalization/context join/dedup
- label quality、group split、Parquet/manifest
- privacy/rights/training eligibility

退出：数据可追溯、无项目泄漏、创意分歧保留、合规导出通过。

### Milestone 4 — Calibration

- per-task calibration、slice metrics、threshold candidate
- applicable scope、drift baseline、dashboard

退出：独立测试、严重错误 slice、数据充分性和复现通过；不足模块保持 shadow。

### Milestone 5 — L2/L3 Routing

- effective policy、routing audit
- risk-stratified sampling、drift、downgrade、kill switch

退出：边界、blocker precedence、抽样权重、漂移和自动降级演练通过。

### Milestone 6 — Evaluation and Candidate Release

- MLflow/Artifact integration、evaluation plan
- candidate/champion、approval、canary、promotion/rollback

退出：candidate→eval→approval→canary→rollback 全链路与权限分离通过。

### Milestone 7 — Online Performance

- connector/raw ingest/variant resolution
- metric quality、comparison/experiment、applicable scope

退出：合法性、数据质量、可复现分析和因果表述边界通过；无数据时不阻断主线。

### Milestone 8 — Production Qualification

- end-to-end monitoring、alerts/runbooks、security/DR
- module-level L2/L3 canary、人工 workload/quality comparison

退出：系统证明自动化未降低 blocker 控制，Release Gate 始终人工，治理报告获批准。

---

## 3. 验收矩阵

| 维度 | 必须证明 |
|---|---|
| Quality Event | taxonomy、定位、Evidence、状态、修正路由 |
| Blocker | 故障集覆盖、严重漏检、unavailable fail closed |
| Correction | before/after、上下文、分歧、lineage、隐私/rights |
| Calibration | task scope、独立测试、误差、严重 slice、充分性 |
| Routing | Policy snapshot、blocker precedence、幂等、审计 |
| Sampling | 风险分层、抽样概率、加权估计、人工覆盖 |
| Drift | feature/quality、降级、回顾审核、非自动恢复 |
| Evaluation | frozen plan、candidate/champion、slice、复现 |
| Release | RBAC、canary、hard stop、promotion、rollback |
| Online | Variant 关联、定义、窗口、混杂、适用范围 |
| Governance | 权限、审计、隐私、安全、成本、DR |

---

## 4. 端到端验收场景

1. 从历史 Review/Correction 构建冻结 Dataset。
2. 运行 blocker detector 与 Confidence shadow benchmark。
3. 注入高置信度严重错误、检测器不可用和稀有类型 slice。
4. 训练/选择校准器并提出模块级 L2 ThresholdCandidate。
5. 审批后 canary，验证风险抽样和 RoutingAudit。
6. 注入 correction spike、feature drift 和 Provider 版本变化。
7. 系统必须自动降级到 L1，生成回顾审核且禁止自动恢复。
8. 创建 Prompt/Config Candidate，完成配对评测、人工审批和回滚。
9. 接入一组合法线上数据，区分 summary/comparison/A-B experiment。
10. 验证线上结果只产生候选优化，Release/Fact/Story 不被修改。

不得出现：自评分自批准、缺数据硬上线、固定随机抽样冒充风险抽样、指标恢复后自动升级、线上高播放覆盖 blocker、自动 Release。

---

## 5. 自动化升级门槛

每个 module/task/scope 单独签收，至少要求：

- 预注册最小样本和稳定观察窗口；
- 足够严重错误/边界样本与类型/平台/语言覆盖；
- calibration 与 severe false negative 达标；
- required detectors 可靠且 unavailable 有 fail-closed；
- L3 sampling 能估计总体风险并覆盖稀有/漂移 slice；
- downgrade、kill switch、review capacity 和 rollback 已演练；
- 人工审核负担下降且 correctness 不回归。

未满足时继续 L1/shadow，不以项目进度为理由放宽。

---

## 6. 性能与容量

报告 detector/router 实时延迟、离线 benchmark/calibration 吞吐、模型/token/cost、Dataset 构建时间、Review queue、sampling workload、dashboard lag 和 DR 恢复时间。

离线评测按 shard 并发且有预算/背压；实时路由必须低延迟、高可用，故障时回到保守模式。具体 SLO 由实测 Capacity Profile 固定。

---

## 7. 回滚与灾难恢复

- Prompt/Model/Config/Rubric/Calibration/Policy 以完整组合版本回滚。
- 回滚创建新 active pointer/Audit，不修改历史 Run/Decision。
- 严重错误可通过 kill switch 立即降到 L1/Champion。
- Rights/security 事件可覆盖运行 snapshot，但必须审计和回顾。
- PostgreSQL/Object Store/MLflow 恢复后校验 Dataset、Approval、Policy、checksum 和 lineage。

---

## 8. 完成定义

- 所有 Milestone、验收矩阵、安全和 DR 演练通过。
- 至少一个低风险模块完成 L2 canary；若数据不满足，保持 L1 也可完成基础建设，但不得宣称 L2 达成。
- 至少一个稳定机械模块完成 L3 风险抽样演练。
- Candidate 发布和回滚可在规定响应时间完成。
- Release Gate 在所有测试中无法被 AI/Router 自动批准。
- 线上数据缺失不影响离线高质量生产系统运行。

---

## 9. 不得以此替代完成

- 人工变少不代表质量自动化成功。
- 平均校准好不代表严重风险 slice 安全。
- 多个 AI reviewer 同意不代表事实正确。
- 有线上相关性不代表存在因果。
- 模型能提出优化不代表可以自行上线。
- L4 不代表无人负责创意和发布。

