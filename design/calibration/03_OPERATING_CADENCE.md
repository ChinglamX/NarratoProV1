# Calibration Operating Cadence

Version: 1.0

## 1. 目标

规定日常生产、版本变更和周期评审中的校准操作，确保系统长期记住质量边界并在漂移或严重错误时及时降级。

输入：Production Runs、Review/Correction、Shadow/Canary decisions、Version Changes、Drift/Online Metrics。

输出：Daily/Release/Periodic Reports、Downgrade/Review Actions、Candidate Backlog、Calibration Pack Updates。

---

## 2. 每次运行

- 固定 EffectiveConfig/Model/Prompt/Policy/Calibration snapshots。
- 记录 Prediction、Confidence、Routing 和 required checks。
- 结构化保存人工 Decision/Correction 和耗时。
- S0/S1 立即进入 incident/feedback queue。
- 生产结果不直接修改 Calibration/Policy。

---

## 3. 每次版本变更

适用于模型、Prompt、Config、Schema、Provider、字体/媒体工具和 Quality Rubric：

1. 判断 Calibration scope 是否失效。
2. 运行 compatibility/golden/frozen benchmark。
3. Candidate 与 Champion 配对比较。
4. 检查 S0/S1 和关键 slice 回归。
5. 审批、canary 和风险抽样。
6. 晋级或回滚。

未经评测的改变保持 research/shadow，不能继承旧的 calibrated 状态。

---

## 4. 每周/每批生产复盘

按 module/type/provider 汇总：S0/S1、Correction Rate、Review Precision、Automation Coverage、high-confidence errors、unavailable、人工耗时、成本和常见操作。

输出 Top Error Patterns 和 Candidate Backlog。至少重复或高影响问题才进入优化，避免追逐单个偏好样本。

---

## 5. 每月/稳定窗口评审

- Calibration/reliability 与 slice coverage。
- L2/L3 sampled error 的加权估计。
- drift/OOD、Provider failure 和数据结构变化。
- Reviewer agreement/guideline drift。
- Calibration Pack 是否需要扩充新类型/平台/语言。
- Candidate rollout/rollback 和资源成本。

升级建议必须包含数据、风险、适用范围和回滚；指标稳定不能自动升级。

---

## 6. 即时降级触发

- 高置信 S0 错误。
- required detector unavailable 或 blocker miss。
- 新输入超出 ApplicableScope。
- Correction/Provider failure 突增。
- Model/Prompt/Config 未评测变化。
- Rights/security 异常。

动作：scope kill switch → L1/Champion → 受影响 artifact 回顾审核 → incident/root cause → 新 Candidate/Calibration。恢复仍需审批。

---

## 7. 线上数据节奏

只有数据质量、Variant 关联和窗口成熟后进入分析。先输出 Performance Summary/Comparison；只有 assignment 和统计设计成立才输出 Experiment Result。

线上结果进入 Candidate Backlog，不直接修改 Story、Profile、Prompt 或 Production pointer。

---

## 8. 责任与签收

- System Engineer：数据/指标/版本/路由和技术安全。
- Drama Producer：Strategy、Hook、Timeline、Narration 创意 gold。
- Review Director：独立 blocker/Craft 复核、分歧与发布质量。
- Human Owner：Automation Policy、候选上线和 Release 最终决策。

同一 Candidate 作者不能单独完成最终签收。

---

## 9. 测试与验收

- 模拟版本变化使旧 Calibration 正确 drift/shadow。
- 注入 S0 后 kill switch、L1 降级和回顾审核成功。
- 周/月报告可从 immutable records 重建。
- 线上高表现不能覆盖 offline blocker。
- Candidate Backlog 与实际审批/回滚 lineage 完整。
- 无人工审批不能恢复更高自动化等级。

