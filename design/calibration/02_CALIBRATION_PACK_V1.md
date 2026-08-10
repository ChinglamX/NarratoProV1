# Calibration Pack v1

Version: 1.0

## 1. 目标

定义系统实现后第一份可执行校准包，建立真实质量 baseline、错误 taxonomy、Frozen Test 和 Shadow Confidence 数据。

输入：首批合法短剧、demo、标注人员、系统 Champion versions、Annotation/Quality Profile。

输出：CalibrationPackRef、Dataset Manifests、Guidelines、Gold Artifacts、Baseline Reports、L2 Readiness Matrix。

---

## 2. 内容结构

```text
calibration_pack_v1/
├── manifest.yaml
├── rights_and_usage.yaml
├── split_manifest.yaml
├── slice_catalog.yaml
├── guidelines/
├── gold/
│   ├── media_perception/
│   ├── fact_story/
│   ├── strategy_hook/
│   ├── timeline_narration/
│   └── voice_audio_subtitle_render/
├── fault_injection/
├── predictions/
├── reviews_corrections/
└── reports/
```

实际大文件位于 Object Store，目录表示逻辑 Manifest，不要求媒体进入 Git。

---

## 3. 样本选择

- 5–10 部代表性短剧；不足时允许分阶段扩充，但必须声明 scope。
- demo 作为 Craft reference。
- 至少包含正常、边界和已知失败样本。
- 困难 slice：多人物/换装/遮挡、倒叙/梦境/说谎/身份揭示、方言/BGM/重叠语音、手机/文件/艺术字、多人竖裁、复杂字幕、TTS 专名。
- 权利记录必须明确允许内部分析/评测；训练使用另行判断。

---

## 4. 建设批次

### Pack A — Foundation Faults

Schema、checksum、stale version、retry、media corruption、sync、loudness、subtitle bounds、rights 和 render failures。可在 Stage 1/5 通过合成故障较早建立。

### Pack B — Perception and Story

Shot、ASR、OCR、Identity、Event、Causal、Evidence gold。随 Stage 2 首个真实项目建设。

### Pack C — Strategy and Creative

SellingPoint、Strategy/Hook pairwise、Timeline edits、Narration before/after、demo rubric。随 Stage 3/4 建设。

### Pack D — Voice and Final Media

TTS、Alignment、Mix、Subtitle、Render/QC 和完整观看。随 Stage 5 建设。

四个批次共享 pack_id/split policy，可独立版本化，避免等所有模块完成才开始校准。

---

## 5. 标注流程

1. 冻结 Annotation Guideline。
2. 工具展示 source/program、Evidence、版本和 timecode。
3. 至少对 S0/S1 和创意 pairwise 样本进行二次复核。
4. 分歧进入 adjudication/unresolved，不强行多数表决。
5. 生成 AnnotationQualityReport。
6. 冻结 Test manifest 并限制访问/使用目的。

---

## 6. Baseline 运行

每个 Champion Provider/Prompt/Config 在固定 manifest 上运行，记录 prediction Artifact、raw response、资源、成本、版本和失败。全部正式路由仍为 L1；Confidence 处于 shadow。

输出模块报告和总 Readiness Matrix：

```text
module/task
scope
dataset coverage
quality metrics
S0/S1 count
calibration status
recommended level
blocking gaps
next data needed
```

---

## 7. L2 Readiness 判定

只有满足预注册样本、严重错误/困难 slice、Calibration、required detector、fail-closed、review capacity、canary/rollback 的模块标 `ready_for_l2_canary`。

其他状态：shadow_only、insufficient_data、quality_failed、rights_blocked、drifted、research。

Pack v1 不要求所有模块达到 L2。能够诚实证明哪些模块不能自动化也是成功输出。

---

## 8. 验收

- Manifest、rights、split、guideline、gold 和 baseline 完整关联。
- 同一剧/系列无 split 泄漏。
- 所有 S0 blocker 有至少一个正例或明确缺口。
- Frozen Test 未参与 Prompt/阈值选择。
- Baseline 可重放并定位每个错误。
- Readiness Matrix 不以人工介入率单独决定等级。

