# E06 Visual Benchmark v1（真实短剧）

Date: 2026-08-16
Benchmark: `evaluation/benchmarks/e06_visual_v1.json`
Provider admission: OCR/DETECTION/VLM 均 research（基准证据，非生产准入）
Corpus: `data/corpus/`（13 剧 / 36 episodes / ~98 分钟，软链自桌面素材，rights approved per project owner）
Split: `evaluation/corpus/e06_visual/manifest.json`（按剧隔离，DatasetSplitManifest 契约校验）

## 执行

- `scripts/build_e06_benchmark.py`：PySceneDetect 分镜 → 每集采样 ≤20 帧 → PaddleOCR + RT-DETR-L 全帧 → Ark doubao-seed VLM 每剧 ≤4 帧（API 成本控制）
- 全量 36 episodes 处理完成，总采样 720 帧

## 指标（按 split）

| Split | episodes | frames | OCR texts (/frame) | DET boxes (/frame) | VLM claims | errors |
|---|---|---|---|---|---|---|
| train | 14 | 280 | 451 (1.6) | 547 (2.0) | 56 | 0 |
| validation | 10 | 200 | 312 (1.6) | 330 (1.6) | 40 | 0 |
| frozen_test | 12 | 240 | 289 (1.2) | 391 (1.6) | 48 | 0 |
| **合计** | **36** | **720** | **1052** | **1268** | **144** | **0** |

延迟（本地 CPU）：OCR 5.2–7.4s/帧（含模型常驻后实际推理更快，首次加载计入）；
DET 2.9s/帧；VLM API 6.6s/帧。

## 观察与已知项

1. **OCR 有效**：识别出真实字幕文本（如"小伙上山给重伤的嫂子挖草药时"），短剧字幕密度 ~1.2–1.6 文本/帧合理；frozen_test 略低（题材差异）。
2. **DET 计数有效**：~1.6–2.0 框/帧；**label 多为 unknown**——RT-DETR COCO 80 类不含短剧特有类别（道具/场景），后续如需语义标签需微调或类别映射。
3. **VLM 描述质量高**：准确描述场景/人物/氛围（山林雾气、人物关系等），可作为 Shot 级语义证据。
4. **OCR kind 全部标 burned_in_subtitle**（adapter 默认）；`scene_text`/`graphic_overlay` 需后续按位置/时序细化。
5. **0 错误**：720 帧 × 3 provider 全链路无失败（fail-closed 未触发），research 管线稳定。
6. **帧文件为中间产物**：frames/ 每集复用编号（结果已入 JSON，帧目录不保留全量）。

## 用途

- E06 从 research→production 的**证据基线**（后续模型替换/参数调优对比锚点）
- 与 demo benchmark（`e09_demo_v1.json`）的视觉侧对照
- 真实 Corpus 首个版本；扩展素材可重跑 `build_e06_corpus.py` + `build_e06_benchmark.py`

## 后续建议

1. DET label 类别映射/微调（提升语义检测价值）
2. OCR kind 细化（字幕 vs 场景文字）
3. 与 E07 Fact/Identity 融合验证（OCR 文本进 Fact、DET 框辅助 tracklet）
4. Mac mini 容量验收（长视频吞吐基线）后可评估 production 升级

## 增强（enriched，2026-08-16）

`scripts/enrich_e06_benchmark.py` 产出 `e06_visual_v1_enriched.json`：

1. **OCR kind 细化**（region 启发式）：scene_text 562 / burned_in_subtitle 461 / graphic_overlay 29（原全部 burned_in_subtitle）。
2. **DET 语义标签**（Ark VLM 网格标注，每集 2 帧子集）：81 框获得标签（person 61、prop 6、building 3 等；其余保持 unknown，扩展子集可提升覆盖）。
3. **E07 融合验证**：36 episodes × 每集 OCR→Fact 观测 8 条 = **288 个 observable Fact**（`fuse_observations`，FactType.OCR，evidence=字幕文本），证明 OCR→Fact 链路在真实语料上可用。
