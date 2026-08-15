# E06 Semantic Visual Provider Admission Assessment

Date: 2026-08-15
Type: Admission path assessment (no production approval; research/L1 unchanged)
Status: Draft for project-owner decisions

## 1. 结论摘要

E06 视觉 Provider 的**工程契约框架已就绪**（`ProviderPackage` 已承载
code/weight license、commercial 姿态、model checksum、admission 状态），
缺的是**具体 Provider 的准入数据与三个 license/部署决策**。本文给出各能力
差距矩阵、候选 Provider 材料清单、决策点与分阶段准入路径。

现状依据：G04 baseline（`evaluation/reports/G04_VISUAL_BASELINE.md`）、
E06 Acceptance Report（`quality/E06_ACCEPTANCE_REPORT.md`）、G05 probe、
`e06_g05.json` qualification、`packages/contracts/providers.py`。

## 2. 现状盘点（有证据）

| 项 | 状态 |
|---|---|
| Provider 契约框架 | ✅ `ProviderPackage`（identity/capabilities/admission/code+weight license/commercial_use_allowed/model_checksum/data_policy/hardware/deterministic/retry_safe）；`ProviderAdmission` = production/research/blocked |
| Gateway fail-closed | ✅ G01 实现：policy 准入、raw/normalized 隔离、explicit unavailable |
| OCR/detection/tracking/face/embedding/VLM typed contracts | ✅ G04：OCR/TextTrack、Detection、Tracklet、Face、Embedding、VLM claim |
| 本地 research adapter | ✅ OpenCV contour/quality（`opencv_contour.py`，admission=research，Apache-2.0 code，无权重）；typed JSON HTTP adapter（`json_http.py`，provider-agnostic） |
| 真实帧工程基线 | ✅ 单帧 decode/quality 特征（24ms、8 candidates）；**identity usability=false**；仅证明 decode/transport |
| G05 探针 | ⚠️ 4 线程 16/16 成功（P50 8ms/P95 17ms）——**只验线程安全，非生产容量** |
| 生产准入 | ❌ 未选择/固定/许可/基准任何语义视觉 Provider |

## 3. 能力 × 材料差距矩阵

每项生产准入需要：**模型卡（exact revision）+ license 姿态 + 权重 checksum + 本地 runtime 固定 + 真实按剧隔离 benchmark**。

| 能力 | 候选 | 主要差距 | 决策依赖 |
|---|---|---|---|
| OCR | PaddleOCR 3.x / PP-OCRv5 | 无 pinned runtime/checksum；无真实短剧 OCR benchmark（字幕/道具文字） | 本地 runtime 可接受性（Mac mini CPU/Metal） |
| Detection | ~~Ultralytics YOLO~~ → **PaddleDetection RT-DETR** | 无 pinned runtime/checksum；无真实短剧检测 benchmark | ✅ 已决：排除 YOLO（AGPL），选 RT-DETR（Apache-2.0） |
| Tracking | ByteTrack / BoT-SORT | 无选择、无基准 | 依赖 detection 选择 |
| Face/Appearance | insightface / OpenCV face | 无选择、隐私/权利边界需审 | 依赖真实项目需求 |
| Visual Embedding | OpenCLIP / SigLIP | 无选择、无基准；embedding≠identity（ADR-033） | 检索召回基准需真实 Corpus |
| VLM | 火山引擎 Ark 豆包视觉（API） | exact endpoint/API key/成本上限 | ✅ 已决：Volcengine Ark（2026-08-15） |

## 4. 决策点（需项目负责人/法务）

1. **Ultralytics AGPL 姿态**：✅ **已决 2026-08-15 —— 全开源路线，不采用商业化**。YOLO（AGPL）排除，Detection 候选切换为 **PaddleDetection RT-DETR**（Apache-2.0）。
2. **OCR 运行时**：PaddleOCR（Apache-2.0）本地固定可接受？—— ✅ 符合开源路线（未决：具体 runtime 固定与性能验收）。
3. **VLM 部署**：✅ **已决 2026-08-15 —— 火山引擎（Volcengine Ark）豆包视觉模型 API**（external_cloud、帧外传、数据驻留 CN）；待定：exact endpoint、API key、成本上限。
4. **容量目标**：Mac mini 长视频/多项目吞吐、峰值 RAM/Metal、成本每分钟——需定义目标值后才能做容量验收（G05 blocker #4）。
5. **benchmark pack**：真实短剧（合法处理权）系列隔离的开发/验证/冻结集——素材与标注是硬前置。

## 5. 建议准入路径（分阶段，均不合成批准）

- **阶段 A（无依赖，可立即）**：为每个候选 Provider 建立 `ProviderPackage` 声明骨架
  （admission=research/blocked，license 字段按已知事实填，checksum/benchmark 留空并校验 fail-closed），
  产出"准入材料清单"模板——工程可做，不碰模型。
- **阶段 B（需素材/决策）**：真实短剧 benchmark pack + 按剧隔离 split；
  license 决策后固定 1–2 个 Provider，补 checksum 与本地 runtime 安装。
- **阶段 C（需证据）**：真实 benchmark 达标 + 容量验收 + Worker 故障注入后，
  提交新 E06 Acceptance Report（engineering recommendation + human signoff）。
  任何阶段都遵守 ADR-032：Agent 不合成生产批准。

## 6. 阶段进展

- **阶段 A（已完成 2026-08-15）**：Provider 准入注册表（`packages/providers/admission.py`）+ production 完整性 gate（gateway 强制校验）。
- **阶段 B 部分完成（2026-08-15）**：本地 runtime 已安装并验证——
  - PaddleOCR 3.7.0 / PaddleX 3.7.2 / paddlepaddle 3.3.1（arm64 CPU）：PP-OCRv6_medium_det + PP-OCRv6_medium_rec 权重已固定（checksum 见注册表），demo 帧推理 1.46s，识别文本可用。
  - RT-DETR-L（PaddleX 内置）：权重已固定（checksum 见注册表），demo 帧 2 个检测（score 0.94/0.81）。
  - 依赖记录于 `pyproject.toml` `[research]` extra；模型缓存 `.paddlex-cache/`（workspace 内，已 gitignore）。
  - **仍缺**：真实短剧按剧隔离 OCR/detection benchmark（素材前置）、Mac mini 长视频吞吐/容量验收、跟踪/embedding 链路验证。

## 7. 下一步建议（等你决定后执行）

1. 批准阶段 A：我产出候选 Provider 的 `ProviderPackage` 声明骨架与准入材料清单模板。
2. 决策上述 5 个决策点（至少 1/2/3）。
3. 提供/指定真实短剧素材来源与标注方式（阶段 B 前置）。
