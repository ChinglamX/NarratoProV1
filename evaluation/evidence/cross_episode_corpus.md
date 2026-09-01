# 跨集 Identity/Story 语料证据包（山神印，research）

Date: 2026-08-19（State v108）
目的：汇总《山神印觉醒后满山风月皆归我》跨集语料的现有真实证据与 identity admission 的缺口，供「跨集 Identity/Story corpus 生产验收」决策使用。

## 1. 语料资产盘点

| 资产 | 范围 | 证据状态 |
|---|---|---|
| Corpus 登记 | `data/corpus/e06-series-01`（e01/e02/e03/hot，evaluation 权利 approved，2026-08-15） | ✅ manifest 已登记 |
| Desktop 授权素材 | 又子剧场/男频/山神印 1–8 集（authorized by owner） | ✅ 有真实 ingest 记录（ep7/ep8） |
| **真实定时 ASR（paraformer-large）** | **ep2 / ep3 / ep7 / ep8**（+ E09 demo 集） | ✅ `evaluation/evidence/speech_baseline/`（20/27/19/17 段 + 说话人分离） |
| 整剧 Story 分析 | 1–8 集主路线：觉醒山神印→驱狼→≥50 年野山参变现→守护妹妹 | ✅ `outputs/series_analysis/SERIES_STORY_STRATEGY_REVIEW.md`（含「千年参王」事实漂移排除） |
| Approved Story | ep8 transcript-grounded factual summary（Gate 1） | ✅ `c378ba51…@1` |
| 跨集候选 | held-out ep7 候选 + canonical E10/E11（40s，useful） | ✅ State v82–v84 |
| 人物检测（research） | 基准 v1 1268 框；enriched 61 person 标签（VLM 打标，自指链待人工抽查） | ✅ benchmark v1/enriched |

## 2. Identity admission 缺口（跨集人物身份）

| 环节 | 现状 | 决策/依赖 |
|---|---|---|
| 人物检测 | research（RT-DETR-L，person 标签覆盖不足——D6 类别体系未决） | D6 |
| Tracklet（跨帧跟踪） | bytetrack `pending-pin`（未 pin、未安装验收、无真实基准） | 需 pin + 真实基准决策 |
| 人脸/外观 embedding | openclip `pending-verify`（recall-only，非 identity，ADR-033） | 需 pin + 基准 |
| 身份装配 | H01/H02 保守装配已实现（仅人工 `corrected_same` 可合并，cannot-link 优先） | ✅ 契约/工程就绪，缺真实语料输入 |
| 人工纠正语料 | 无（跨集同人标注未投入） | 绑定 D5 标注预算 |
| Story 验收 | ep8 factual summary 已批准；**不覆盖人物身份/因果弧**（Gate 1 范围声明） | 需 identity 语料 + Story 阈值 |

## 3. 可直接执行的下一步（部分不依赖决策）

1. **补录 5 集 ASR 段落到 Story 事件映射**（research，已具备数据）：用 `produce_vc003_asr_evidence.py` 模式对 ep2/ep3/ep7 的 ASR 段落做关键词→事件窗口映射，形成跨集「事件时间证据」语料（人工审阅后可用）。
2. **D6 决定 person 类别覆盖**（决策）。
3. **bytetrack/openclip pin + 真实基准**（决策 + 工程）。
4. **人工同人标注**（决策，绑定 D5）。
5. 以上齐备后跑 H01/H02 真实语料装配 → E07 production 验收。

## 4. 边界

- 全部 research：检测/VLM/ASR 未 production admission；confidence unavailable。
- 身份未证明：任何自动装配不得声明身份（ADR-033），仅产出候选供人工 `corrected_same`。
- Release Gate 3 永远人工。
