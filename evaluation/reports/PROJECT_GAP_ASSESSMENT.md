# 项目差距评估（距生产闭环）

Date: 2026-08-16
依据：DEVELOPMENT_ROADMAP（六阶段生产验收）、PRODUCT_CAPABILITY、PROJECT_STATE v56、本会话真实执行证据（E09 认证、E06 provider/benchmark/enrich、E07 fusion proof）

## 1. 六阶段完成度（工程 vs 生产）

| Stage | 工程实现 | 生产验收 | 关键缺口 |
|---|---|---|---|
| S1 Production Foundation（E00–E05） | ✅ 100%（真实 PG/Temporal/Worker 验收） | ✅ 已签收 | 无 |
| S2 Drama Intelligence（E06/E07） | 🟡 工程 ~90%（观察/身份/Fact/Story 全实现） | ❌ 0% | **Provider 未生产准入**（OCR/det/VLM 仅 research，有真实 benchmark v1 但未升级）；Speech benchmark 缺；跨集身份/Story 真实验收缺 |
| S3 Marketing Intelligence（E08） | ✅ 工程 100%（strategy/hook/比较/Gate2） | ❌ 0% | 无真实 Approved Story 输入；Hook 效果数据缺；人工一致性阈值未建 |
| S4 Creative Timeline（E09） | ✅ 工程+真实认证（30.27s preview、人工签署、多 Variant replay） | 🟡 ~50% | **craft 评分人工签核 pending**；素材选择仍用 research provider |
| S5 Audio/Subtitle/Render（E10/E11） | 🔴 仅契约 baseline（~15%） | ❌ 0% | **TTS/alignment/mix/subtitle/ASS/render 主实现全部未开始** |
| S6 Quality Automation | 🔴 设计 ~30% | ❌ 0% | 反馈闭环、Confidence 校准、L2+ 自动化未实现 |

## 2. 核心链路完成度（Media → … → Release）

```
Media ✅ → Observation 🟡 → Fact/Story 🟡 → Strategy 🟡 → Timeline 🟢
→ Voice/Audio/Subtitle 🔴 → Render 🔴 → Quality 🟡 → Release 🔴(流程有，未真实执行)
```

- **可用到**：Timeline + 真实 Preview（30.27s，无配音/混音/最终渲染）
- **距最小生产闭环（一部可发布营销成片）**：约 **45–55%**——缺 TTS 配音、混音、字幕渲染、最终成片渲染、完整 QC 与 Release 真实执行
- **距规模化高质量生产**：更远（Provider 准入、真实语料、容量、反馈）

## 3. 本会话实际推进（E06 前置链）

- 视觉 Provider 真实化：PaddleOCR/RT-DETR 本地安装+checksum、VLM 火山方舟验证、typed adapter 接入 workflow
- 真实 Corpus：13 剧/36 集/98 分钟，按剧隔离 split
- **E06 视觉 benchmark v1**：720 帧三 provider 0 错误；enrich 后 OCR kind 三分、81 语义标签、**288 Facts（OCR→Fact 融合证明）**
- 意义：E06 从"无数据"进入"有真实基准"；E07 融合链首次真实数据可用；E09 语义视觉 blocker 的数据基础就绪

## 4. 关键阻塞排序（影响推进优先级）

1. **E10/E11 主实现（最大工程缺口）**：解锁配音/混音/字幕/渲染，是"能出成片"的硬门槛
2. **E06 Provider 生产准入**：现在有真实 benchmark v1 证据——可推进 research→production 评估（OCR/det/VLM 的 admission 决策）
3. **E07/E08 真实数据验收**：需真实 Approved Story 输入跑通（依赖 2 + identity corpus）
4. **E06 Speech benchmark**（FunASR research 已跑，缺真实 Speech 基准 + rights）
5. **Stage 6 自动化**（反馈/校准/L2+）：依赖 2–4 的数据积累

## 5. 建议推进顺序

A. **E10 非 Provider 工程**（alignment/conform/subtitle 契约驱动实现，不依赖真实 TTS 即可做）→ 与 B 并行
B. **E06 admission 升级评估**（用 benchmark v1 证据评审 OCR/det/VLM production 资格）
C. E07 identity/story 真实 Corpus 验收（依赖 B 的 person 检测 + OCR Fact）
D. E10 TTS 接入（需要 TTS Provider 选择——开源/API 决策）
E. E11 render 落地 + 完整 QC → 首个可发布候选
F. Stage 6 校准/反馈（数据积累后）

## 6. 一句话

**工程地基（S1）与创意时间线（S4）已扎实，但生产闭环卡在"后半段"：E10/E11 未实现 + Provider 未准入 + 真实语料验收未完成——当前最接近的里程碑是 E10 的 alignment/conform/subtitle 链路 + E06 admission 升级评估，两者并行可让"能出带配音字幕的成片"成为现实。**
