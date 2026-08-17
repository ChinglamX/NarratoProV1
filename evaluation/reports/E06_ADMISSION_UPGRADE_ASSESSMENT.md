# E06 Provider 生产准入升级评估（research → production）

Date: 2026-08-16
Type: 只读证据审查（不修改代码、不改变 admission 状态）
Status: Draft for project-owner decisions（需项目负责人批准后才可执行升级）
依据文件（事实来源，未引用外部数据）：
- `packages/providers/admission.py`（准入注册表 + `production_readiness_gaps`）
- `packages/contracts/providers.py`（`ProviderPackage` / `ProviderAdmission` / `ProviderDataPolicy`）
- `evaluation/benchmarks/e06_visual_v1.json`、`evaluation/benchmarks/e06_visual_v1_enriched.json`
- `evaluation/reports/E06_VISUAL_BENCHMARK_V1.md`、`evaluation/reports/E06_VISUAL_PROVIDER_ADMISSION_ASSESSMENT.md`
- `evaluation/qualification/e06_g05.json`、`quality/E06_ACCEPTANCE_REPORT.md`、`evaluation/reports/G04_VISUAL_BASELINE.md`、`evaluation/reports/G05_ENGINEERING_PROBE.md`、`evaluation/reports/PROJECT_GAP_ASSESSMENT.md`
- `packages/evaluation/visual_metrics.py`、`packages/intelligence/facts.py`、`scripts/build_e06_benchmark.py`、`scripts/enrich_e06_benchmark.py`

> 结论先行：**三个 Provider（PaddleOCR PP-OCRv6 / RT-DETR-L / Volcengine doubao-seed VLM）均不具备从 research 升级 production 的证据条件，全部维持 research，均属"需补材料"**。benchmark v1/enriched 是**工程稳定性与真实数据基线**的有效证据，但不是**质量达标证据**（无人工标注基线，无法计算 CER/mAP/claim 正确率，无阈值）。代码级硬缺口：commercial_use_allowed 已 3/3 批准（2026-08-16 owner）；剩余为 VLM 的 checksum/weight_license（2 项硬缺口）。

---

## 1. 评估框架

### 1.1 代码级准入 gate（`production_readiness_gaps`，fail-closed）

对任一 Provider 声明为 `production` 前必须全部满足：

| # | 条件 | 硬缺口表现 |
|---|---|---|
| G1 | `model_checksum` 非空 | `model_checksum is required for production admission` |
| G2 | `weight_license` 非空 | `weight_license is required for production admission` |
| G3 | `commercial_use_allowed = true` | `commercial_use_allowed must be explicitly approved` |
| G4 | code/weight license 无 `pending` 标记 | `license posture contains unresolved 'pending' marker` |
| G5 | `identity.version` 为精确固定版本（非 `pending*`） | `exact pinned revision is required (identity.version)` |

另有 `ProviderPackage.enforce_admission_evidence`：production 声明还要求商业批准，且 `identity.model` 非空时必须带 weight_license + checksum。

### 1.2 证据级条件（来自 `E06_VISUAL_PROVIDER_ADMISSION_ASSESSMENT.md` §3 与 `E06_ACCEPTANCE_REPORT.md` re-entry criteria）

每项生产准入需要：**模型卡（exact revision）+ license 姿态 + 权重 checksum + 本地 runtime 固定 + 真实按剧隔离 benchmark**，且**阈值必须来源于由此 baseline 生成的 Quality Profile**（不能由本文档或任何文档臆造）。质量阈值需可计算指标：`packages/evaluation/visual_metrics.py` 已提供 `ocr_character_error_rate`（CER）、`detection_precision_recall`（IoU 0.5）、`vlm_evidence_compliance`，但**均需人工标注基准（ground truth）才能运行**。

---

## 2. 逐 Provider 对照生产准入条件

### 2.1 PaddleOCR PP-OCRv6（`paddleocr` / `pp-ocrv6` / `paddleocr-3.7.0-paddlex-3.7.2`）

| 条件 | 状态 | 事实依据 |
|---|---|---|
| model_checksum | ✅ | det 权重 SHA-256 已 pin（`sha256:85218d…53960`）；rec 权重 SHA 仅记录在 `known_limitations` 文本（`sha256:1b01c7…c7319`），未单独入 `model_checksum` 字段（该字段单值，仅承载 det） |
| weight_license | ✅ | Apache-2.0 |
| commercial_use_allowed | ✅ | True——项目负责人 2026-08-16 批准（Apache-2.0） |
| license pending 标记 | ✅ | 无 |
| identity.version 精确固定 | ✅ | `paddleocr-3.7.0-paddlex-3.7.2`（含 PaddleX 3.7.2 runtime） |
| 本地 runtime 固定 | ✅ | 2026-08-15 安装验证：PaddleOCR 3.7.0/PaddleX 3.7.2/paddlepaddle 3.3.1（arm64 CPU），demo 帧 1.46s，依赖记录于 `pyproject.toml [research]` extra |
| 真实按剧隔离 benchmark | ✅（工程证据） | v1：720 帧 1052 OCR 文本、0 错误；**质量证据缺人工标注** |
| registry 声明一致性 | ✅ | 2026-08-16 已随 benchmark v1 更新：`known_limitations` 记录 v1 证据（1052 texts）+ CER/阈值/容量待补；`supported_languages=["zh"]` 已声明（中文短剧字幕样本） |

代码级硬缺口（`production_readiness_gaps` 输出）：**G3 已批准（2026-08-16），当前无代码级硬缺口**。

### 2.2 RT-DETR-L（`paddle-detection` / `rt-detr-l` / `paddlex-3.7.2`）

| 条件 | 状态 | 事实依据 |
|---|---|---|
| model_checksum | ✅ | `sha256:51200f…ba19a8` |
| weight_license | ✅ | Apache-2.0 |
| commercial_use_allowed | ✅ | True——项目负责人 2026-08-16 批准（Apache-2.0） |
| license pending 标记 | ✅ | 无（YOLO/AGPL 已排除，2026-08-15 决策） |
| identity.version 精确固定 | ✅ | `paddlex-3.7.2` |
| 本地 runtime 固定 | ✅ | 2026-08-15 demo 帧 2 检测（score 0.94/0.81） |
| 真实按剧隔离 benchmark | ✅（工程证据） | v1：1268 检测框、0 错误；**质量证据缺人工标注框（无 mAP）** |
| 语义标签覆盖 | ⚠️ | v1 全部 `unknown`（COCO 80 类不含短剧专属类别）；enriched 仅 81/1268（6.4%）获 VLM 网格标签 |
| registry 声明一致性 | ✅ | 2026-08-16 已随 benchmark v1 更新：`known_limitations` 记录 v1 证据（1268 boxes、COCO 80 类无短剧类别）+ mAP/阈值/容量待补；detection 语言无关，`supported_languages` 保持空（已注明） |

代码级硬缺口：**仅 G3 1 项**。

### 2.3 Volcengine doubao-seed VLM（`volcengine-ark` / `doubao-seed-2-0-mini` / `doubao-seed-2-0-mini-260428`）

| 条件 | 状态 | 事实依据 |
|---|---|---|
| model_checksum | ❌ | None——API 托管模型，无权重 checksum；`production_readiness_gaps` 直接报硬缺口 |
| weight_license | ❌ | None——API 服务条款（`volcengine-ark-tos`），无模型权重许可证；`production_readiness_gaps` 直接报硬缺口 |
| commercial_use_allowed | ✅ | True——项目负责人 2026-08-16 批准（法务审查通过，所有视频允许） |
| license pending 标记 | ✅ | 无（code_license=`volcengine-ark-tos`，非 OSI 许可证但无 pending） |
| identity.version 精确固定 | ✅ | `doubao-seed-2-0-mini-260428`（endpoint `ep-m-20260716234644-hqltj`） |
| 数据驻留/传输 | ⚠️ | `external_cloud`、仅允许 CN 驻留、`transmits_source_media=True`、`retains_input=True`、`retention_days=30`——**帧外传 + 留存 30 天**，需法务/负责人确认与素材权利一致 |
| 确定性 | ⚠️ | `deterministic=False`——同帧多次调用结果可能不同；生产需重试/一致性策略（`retry_safe=True`） |
| 真实按剧隔离 benchmark | ✅（工程证据） | v1：144 VLM claims（每集 4 帧，全部 `kind=visible`）、0 错误；**质量证据缺 claim 对照标注** |
| 成本 | ⚠️ | `max_cost_micros=10_000_000` 为 benchmark 调用策略值；**成本上限/预算未定**（registry 与 admission assessment 均列"cost caps still pending"） |
| registry 声明一致性 | ✅ | 2026-08-16 已随 benchmark v1 更新：`known_limitations` 记录 v1 证据（144 claims）+ claim 对照/成本/容量待补；`supported_languages=["zh"]` 已声明；`identity.model` 未声明（`enforce_admission_evidence` 因此不会在契约层拦截，靠 `production_readiness_gaps` 拦截） |

代码级硬缺口：**G1 + G2 + G3 共 3 项**（三个 Provider 中最多）。

---

## 3. benchmark v1 / enriched 质量证据评估

### 3.1 已成立的证据（可支撑"工程/稳定性/数据基线"）

1. **真实按剧隔离**：13 剧 / 36 集 / ~98 分钟真实短剧，split 按剧隔离（train 14 集 / validation 10 集 / frozen_test 12 集），由 `DatasetSplitManifest` 契约校验；frozen_test 只测量不调参。✅ 满足"真实按剧隔离 benchmark"的形式条件。
2. **全链路 0 错误**：720 帧 × 3 provider（OCR/DET 全帧、VLM 每集 4 帧）无失败，fail-closed 未触发，research 管线稳定。
3. **OCR 输出真实有效**：识别出真实字幕文本（如"小伙上山给重伤的嫂子挖草药时"），密度合理（frozen_test 1.2 / 其余 1.6 文本/帧；总体 1052 文本 / 720 帧 = 1.46），score 均值 0.8735（n=1043，min 0.1044/max 1.0）。
4. **DET 计数有效**：1268 框（密度 2.0/1.6/1.6 框/帧；总体 1.76），score 均值 0.8320（n=1268，min 0.5003/max 0.9828，阈值 0.5）。
5. **enriched 语义增强**：OCR kind 三分（scene_text 562 / burned_in_subtitle 461 / graphic_overlay 29，原 v1 全部 burned_in_subtitle）；DET 81 框获得语义标签（person 61、prop 6、other 5、building 3、subtitle 2、vehicle 2、animal 1、food 1、weapon 0）。
6. **E07 融合证明**：36 集 × 每集 8 条观测（4 OCR + 4 DET）= 288 个 observable Fact；按 `fuse_observations` 逻辑，OCR 项 → `FactType.OCR`，person 标签检测 → `FactType.PERSON`，其余 → `FactType.ENTITY`。报告措辞"FactType.OCR、evidence=字幕文本"**不精确**（8 条含 4 条检测），288 总数成立。
7. **注册表/契约就绪**：checksum 已 pin（2026-08-15 官方源验证）、typed adapter 已接入 workflow（`VisualObservationWorkflow` e2e complete）。

### 3.2 不能构成"生产质量达标证据"的缺口

1. **无人工标注基线（硬缺口）**：v1/enriched 全部为 Provider 自产输出，无人工 ground truth——
   - OCR：无参考文本 → **无法计算 CER**（`ocr_character_error_rate` 需要 reference）；
   - DET：无参考框 → **无法计算 mAP/precision/recall**（`detection_precision_recall` 需要 reference，IoU 0.5）；
   - VLM：claims 为自由文本描述，**无正确性对照与评分 rubric**（`vlm_evidence_compliance` 需要带 `frame_evidence` 的 `VLMClaim` 对象；持久化 JSON 中 claims 只有 kind/statement/score，score 全为 null，无 frame_evidence，无法直接在该 JSON 上运行该指标）。
2. **无阈值**：frozen_test 存在但未产生任何 pass/revise 阈值；`E06_ACCEPTANCE_REPORT.md` re-entry 明确"阈值必须来源于 baseline 与 Quality Profile"，当前 Quality Profile 无视觉阈值项。
3. **DET 语义标签覆盖不足且证据链自指**：81/1268（6.4%）标签由 **Ark VLM（即被评估的 VLM Provider）** 网格标注生成——用候选 Provider 给另一候选 Provider 打标的证据链，需独立人工抽查；1187 框仍 unknown，COCO 80 类不含短剧专属类别（道具/场景）。
4. **OCR kind 为启发式而非标注**：`enrich_e06_benchmark.py` 按 region 启发式分类（y_min≥0.7 → 字幕；面积≥5% → 图形；否则场景文字），无人工校验。
5. **enriched 帧对应性**：DET 标签网格输入是**重新抽取的帧**（`enrich_NNNN.jpg`），不是 benchmark 原始采样帧（frames/ 为中间产物不保留全量），标签-检测框对应依赖重采样帧内容一致，存在潜在漂移。
6. **VLM 采样受限**：144 claims = 每集 4 帧（`frames[:4]`，全为前 4 个 shot 帧），非随机/分层采样，且无重试一致性评估（deterministic=False 未验证同帧多次调用的稳定性）。
7. **9 条 OCR 无 score**（1052 文本中 1043 条有 score），score 完整性未 100%。

### 3.3 与 demo 对比状态

- `e9_demo_v1.json`（e09-demo-v1）：`human_annotation_status: pending`，`usage: reference comparison only`——demo benchmark 自身**无人工标注**，且是创意层对比样本（`e09_craft_compare_v1.json` 为成片 cut 密度对比，非 Provider 质量），因此**"与 demo 对比阈值"目前不存在**，只有 benchmark 报告的"与 e09_demo 视觉侧对照"意向（`E06_VISUAL_BENCHMARK_V1.md` 用途 2），尚无对照结论。

### 3.4 数据一致性（已核对）

- ~~`E06_VISUAL_BENCHMARK_V1.md` 写"DET 2.9s/帧"~~：已修正（2026-08-16）——报告当前写"DET 均值 771ms/帧（JSON `avg_duration_ms`）"，与 `e06_visual_v1.json` 一致（min 692 / max 937）。OCR 报告 5.2–7.4s vs JSON 均值 6.16s、VLM 报告 6.6s vs JSON 均值 6.63s 均吻合。

---

## 4. 逐 Provider 升级建议

| Provider | 结论 | 理由（一句话） |
|---|---|---|
| PaddleOCR PP-OCRv6 | **保持 research（需补材料）** | 代码级仅缺 commercial 批准，但质量证据只有无标注 counts，无 CER/阈值 |
| RT-DETR-L | **保持 research（需补材料）** | 代码级仅缺 commercial 批准，但无 mAP/阈值，语义标签覆盖 6.4% |
| Volcengine doubao-seed VLM | **保持 research（需补材料最多）** | 代码级 3 项硬缺口（checksum/weight_license/commercial），数据驻留与成本未决 |

### 4.1 PaddleOCR PP-OCRv6 缺口清单

1. ~~`commercial_use_allowed`~~（2026-08-16 已批准，Apache-2.0）。
2. **人工标注 OCR 基线**（frozen_test 子集标注参考文本）→ 计算 CER → 定阈值（阈值来源于 Quality Profile）。
3. Mac mini 容量验收（长视频吞吐、P50/P95、RAM/Metal、成本/分钟）——`e06_g05.json` `resource-cost-baseline` 仍 blocked、`long-series-concurrency` 仍 not_evaluated。
4. `known_limitations` 更新（benchmark v1 已存在）；rec checksum 单独记录（或扩展 registry 以承载多权重 checksum）；`supported_languages` 声明中文。
5. 修正 benchmark 报告数据不一致（如涉 DET 延迟仅 DET 部分，OCR 无需）。

### 4.2 RT-DETR-L 缺口清单

1. `commercial_use_allowed` 批准（同 OCR）。
2. **人工标注检测框基线**（frozen_test 子集）→ mAP/precision/recall（`detection_precision_recall`，IoU 0.5）→ 定阈值。
3. **语义类别体系决策**：COCO 80 类映射 / 微调 / 扩展 VLM 标注子集（当前 6.4% 覆盖不足；enriched 标签需人工抽查以解除"自指证据链"）。
4. 容量验收（同 OCR，G05 探针 16/16、P50 8ms/P95 17ms 只验线程安全，非容量）。
5. `known_limitations` 更新。

### 4.3 Volcengine doubao-seed VLM 缺口清单

1. **`model_checksum` / `weight_license` 硬缺口**：API 托管模型无权重文件——需项目负责人决策**等价固定证据**（如 endpoint + model id + API schema 版本 + TOS 版本记录），并确认 `production_readiness_gaps` 是否对 API 型 Provider 豁免/修订（当前 fail-closed 会拒绝）。
2. `commercial_use_allowed` 批准（含 `volcengine-ark-tos` 商业条款 + 数据驻留 CN + 留存 30 天审查）。
3. **VLM claim 质量对照**：人工评分 rubric（描述正确性/幻觉/关键元素召回），或与 e09 demo 侧对照；`vlm_evidence_compliance` 需在 normalized `VLMClaim`（含 frame_evidence）上运行。
4. **成本上限**：`max_cost_micros` 目标值 + 每媒体分钟成本目标（当前未定）。
5. 非确定性策略：同帧重复调用稳定性测量、重试/一致性策略。
6. 容量/故障注入（`e06_g05.json` `worker-interruption-recovery` 仍 not_evaluated——E03 只证明通用 Temporal restart，未做该 Activity 的 kill/restart/幂等验收）。
7. `known_limitations` 更新；`identity.model` 声明（契约层完整性）。

---

## 5. 需项目负责人决策的点

| # | 决策点 | 说明 | 建议 |
|---|---|---|---|
| **D1** | **是否批准 3 个 Provider 的 `commercial_use_allowed`** | 本地两模型（Apache-2.0）与 VLM（volcengine-ark-tos，帧外传 + CN 驻留 + 留存 30 天）分别批准 | 本地两模型可批准；VLM 建议先过法务条款审查 |
| **D2** | **benchmark v1/enriched 的证据地位** | 接受为"工程/稳定性基线"（可立即采纳）vs 接受为"生产质量达标证据"（当前不能——缺人工标注与阈值） | 接受为工程基线；质量达标另需人工标注 baseline |
| **D3** | **资源/容量与成本目标** | Mac mini 长视频/多项目吞吐、P50/P95、RAM/Metal、成本/分钟、VLM 成本上限——`e06_g05.json` 3 个 capacity 类 check 未关闭 | 定义目标值后做容量验收（G05 blocker #4） |
| D4 | VLM checksum/weight_license 豁免等价物 | API 型 Provider 无权重，`production_readiness_gaps` 当前 fail-closed | 决策是否修订 gate（API 固定证据替代） |
| D5 | 人工标注基线投入 | 规模（frozen_test 子集）、预算、标注协议（OCR 参考文本 / DET 参考框 / VLM rubric） | 最小可行子集起步 |
| D6 | DET 类别体系 | COCO 映射 / 微调 / 扩展 VLM 标注 | 结合 E07 需求（person 检测 + OCR Fact） |
| D7 | 证据卫生 | 修正 DET 延迟报告值、更新 registry `known_limitations`、补充 9 条 OCR score | 升级前置必做 |

---

## 6. 升级前置路径（与既有 re-entry criteria 对齐）

升级必须依次满足（来源：`E06_ACCEPTANCE_REPORT.md` re-entry criteria + `e06_g05.json` blockers）：

1. **关闭 `e06_g05.json` 全部 blocker**：visual-provider-bakeoff（需人工标注基线 + 阈值）、resource-cost-baseline（需容量/成本目标值）、long-series-concurrency（需 Mac mini 验收）、worker-interruption-recovery（需故障注入）、（Speech 侧 benchmark/rights 与视觉升级独立但同属 E06 闭环）。
2. **人工标注 frozen_test 子集** → 在 `e06_visual_v1(_enriched).json` 上运行 `ocr_character_error_rate` / `detection_precision_recall` / `vlm_evidence_compliance` → 生成 Quality Profile 阈值。
3. **更新注册表**：`commercial_use_allowed=true`（批准后）、`known_limitations` 修正、VLM gate 修订（如 D4 决策）、`identity.model`/`supported_languages` 补全。
4. **新 E06 Acceptance Report**（engineering recommendation + 人工签名），`automation_level` 维持 L1、`confidence_shadow` 维持 Shadow 直至另行批准。
5. 全程遵守 ADR-032：Agent 不合成生产批准，升级动作本身需项目负责人签字。

---

## 7. 一句话结论

benchmark v1/enriched 把 E06 从"无数据"推进到"有真实按剧隔离的工程基线"（720 帧 0 错误、1052 OCR、1268 DET、144 VLM claims、288 Facts），但**三个 Provider 距离 production 都还差"人工标注基线 + 阈值 + commercial 批准 +（VLM）API 准入等价物与容量/成本目标"**——本轮评估结论：**三者均维持 research，需补材料**。
