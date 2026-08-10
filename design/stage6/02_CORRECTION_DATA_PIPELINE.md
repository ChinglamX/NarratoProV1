# Correction Data Pipeline

Version: 1.0

## 1. 目标

把 Story、Strategy、Timeline、Voice、Audio、Subtitle、Render 和 Release 审核中的人工修正转换为结构化、可训练/评测、可治理的数据，而不是只保存自然语言意见。

输入：ReviewDecision、CorrectionRecord、before/after Artifact、Audit/Run/Provider context、reviewer metadata。

输出：NormalizedCorrection、Training/Evaluation Example、CorrectionDatasetVersion、AnnotationQualityReport、FeedbackAggregate。

---

## 2. Correction Contract

至少包含：correction_id、project/run/variant、module/dimension、target before/after refs、semantic operation、before/after typed values、reason taxonomy/free text、time/source range、severity/blocker、model/prompt/config/profile/policy versions、reviewer、created_at、dependency impact 和 consent/usage flags。

自然语言理由是补充，不得替代 semantic operation。无法结构化的修正进入 `other/unresolved` 队列，不强行错标。

---

## 3. Taxonomy

示例：

- Story：identity_merge/split、event_missing/wrong、causal_wrong、timeline_wrong；
- Strategy：selling_point_replace、direction_change、hook_change、spoiler；
- Timeline：clip_replace/trim/move、crop_keyframe、beat_duration、transition；
- Narration/Voice：fact、redundancy、tone、pronunciation、take_selection；
- Audio/Subtitle：gain/ducking、asset_replace、cue_split、timing/layout/style；
- Release：technical、rights、creative、platform blocker。

Taxonomy 版本化并允许多标签；迁移不得丢失原始 Correction。

---

## 4. 数据管线

```text
Immutable Correction Event
→ Schema/Reference Validation
→ Context Snapshot Join
→ PII/Rights/Consent Filtering
→ Taxonomy Normalization
→ Reviewer Quality/Disagreement
→ Dataset Split and Dedup
→ Versioned Parquet + Manifest
→ Evaluation/Training Eligibility
```

PostgreSQL 保存事务与索引；Object Store 保存大 payload；Parquet/DuckDB 用于离线分析。Artifact Registry 保存 Dataset Manifest 和 lineage。

---

## 5. 防泄漏与拆分

按项目/剧/系列分组拆分 train/dev/test，避免同剧相邻镜头和相似 Variant 泄漏。测试集冻结，不能用来反复调阈值后继续声称独立验证。

同一 Correction 的撤销、重复提交和后继版本需要关联，避免被误算为多个独立样本。

---

## 6. 标注质量

记录 reviewer expertise、guideline version、agreement、adjudication 和 unknown。创意偏好保存 pairwise/choice + reason，不强制转成唯一“正确答案”。

高置信度严重错误、权利/事实 blocker 和关键自动路由样本优先二次复核。Reviewer 自身偏差和概念漂移需要监控。

---

## 7. 隐私、权利与保留

- 数据最小化：只导出评测所需上下文。
- 角色、访问、脱敏、保留期、legal hold 和删除请求可执行。
- 素材/语音/人物数据的授权范围决定是否可用于训练、仅评测或完全禁止。
- 云端评测/训练前执行 data residency 和 provider policy。
- 删除请求使用 lineage 找出派生 Dataset；不能只删原记录。

---

## 8. 并发与增量

Correction normalization 按事件并行；Dataset build 在 manifest snapshot 上批处理。新 Correction 形成新 dataset version，不原地追加改变已发布 benchmark。

重复/乱序事件通过 correction_id/idempotency 去重。Join 缺失上下文时标 incomplete，不猜测模型/配置版本。

---

## 9. 测试与验收

- 所有模块 Correction 可结构化 round-trip。
- 撤销、重复、并发和 taxonomy migration。
- project/series group split 无数据泄漏。
- PII/rights/consent 规则阻止不合规导出。
- Dataset Manifest 可定位回 before/after 和运行环境。
- 创意分歧不会被错误压成二元事实标签。

