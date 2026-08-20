# Provider / 语料形式化准入决策包（D2–D9）

Date: 2026-08-19（State v107）
性质：证据汇总 + 决策点 + 建议动作。**决策权在项目负责人**（ADR-032：Agent 不合成生产批准）。批准后执行升级，不批准则维持 research（当前 canonical 链以 research 调用、输出经人工 QC 与 checkpoint，可继续）。
前置文档：`E06_ADMISSION_UPGRADE_ASSESSMENT.md`、`packages/providers/admission.py`、`evaluation/evidence/`、`evaluation/qualification/e06_g05.json`、`PROJECT_GAP_ASSESSMENT.md`。

---

## 0. 已就绪证据清单（决策前可复核）

| 证据 | 位置 | 说明 |
|---|---|---|
| IndexTTS-2 权重 checksum（6 文件 + 清单） | `evaluation/evidence/indextts_weights_manifest.txt`；注册表 `model_checksum=294cea17…` | `shasum -a 256` 可复验；`production_readiness_gaps(indextts)=0` |
| FunASR 候选登记 | `packages/providers/admission.py`（funasr，research，3 gaps） | paraformer-large + VAD/PUNC + campplus 说话人 |
| 真实 Speech 基准 5 集 | `evaluation/evidence/speech_baseline/` | 定时 ASR + 说话人分离（30/20/27/19/17 段）；Episode 8 对白命中人工窗口 overlap 0.816/0.78/0.388 |
| 视觉 benchmark v1/enriched | `evaluation/benchmarks/e06_visual_v1(_enriched).json` | 720 帧、1052 OCR、1268 DET、144 VLM claims、0 错误（工程基线） |
| Episode 8 真实链路证据 | `outputs/vc003_episode_08/` | Gate1→2→E09→E10→E11 全链 + useful；自动选镜/Timeline 草稿 `eefec351…` |
| 自动内容生成 research | `packages/intelligence/vlm_clip_retrieval.py`、`narration_draft.py` | 选镜（ASR 证据窗口 + VLM 精修）与解说草稿（规则校验）已实测 |

---

## 1. 决策点与建议（D2–D9）

### D2 — benchmark v1/enriched 的证据地位
- **状态**：v1/enriched 为 Provider 自产输出，无人工标注，只能算工程/稳定性基线。
- **建议**：接受为「工程/稳定性基线」（可引用）；生产质量达标证据另需 D5 人工标注。
- **批准后动作**：注册表 `known_limitations` 标注基线地位；质量阈值仍挂起。

### D3 — 容量/成本目标（Mac mini + VLM 成本上限）
- **状态**：`e06_g05.json` 的 resource-cost-baseline / long-series-concurrency 未关闭；VLM `max_cost_micros` 无目标值。
- **建议**：按 State §6 已授权目标（OCR P95 ≤10s/≤15s、DET ≤1.5s/≤8s、内存 ≤4GB/≤12GB、吞吐 ≤5/≤10min 每集、VLM ≤¥0.5/集）执行容量验收；VLM 成本上限给一个目标值（如 ≤¥0.5/集）。
- **批准后动作**：跑 `scripts/probe_e06_capacity.py`（已有）→ 归档结果 → 更新 G05 报告。

### D4 — VLM（API 型）checksum/weight_license 豁免等价物
- **状态**：volcengine-ark 为 API 托管，无权重文件，`production_readiness_gaps` 报 checksum/weight_license 两项硬缺口（fail-closed 会拒绝 production 声明）。
- **建议**：决策「API 固定证据替代权重 checksum」：endpoint + model id + API schema 版本 + TOS 版本 + 调用记录 checksum；修订 `production_readiness_gaps` 以支持 API 型 Provider。
- **批准后动作**：注册表 volcengine-ark 录入固定证据；`production_readiness_gaps` 增加 API 分支 + 测试。

### D5 — 人工标注基线投入（OCR/DET/VLM frozen_test 子集）
- **状态**：无人工参考，CER/mAP/claim 对照无法计算。
- **建议**：投入最小可行 frozen_test 子集（如 12 集 × 每集 8 帧）：OCR 参考文本、DET 参考框（IoU 0.5）、VLM claim rubric。
- **批准后动作**：标注 → 在 benchmark JSON 上运行 `packages/evaluation/visual_metrics.py`（CER/mAP/`vlm_evidence_compliance`）→ 生成 Quality Profile 阈值。

### D6 — DET 类别体系（COCO 80 无短剧类别）
- **状态**：v1 标签 1187/1268 unknown；enriched 81 框 VLM 标签（person 61 等）但自指证据链（VLM 给 DET 打标）。
- **建议**：决策方向——(a) COCO 映射（只保留 person/vehicle 等可用类）；(b) 微调/自定义类别（需标注数据，绑定 D5）；(c) 扩展 VLM 标注子集 + 人工抽查。
- **批准后动作**：按选定方向更新检测 adapter 标签映射 + 重跑子集 benchmark。

### D7 — 证据卫生
- **状态**：部分完成（DET 延迟报告已修正、registry known_limitations 已随 benchmark 更新）。
- **建议**：补 9 条 OCR score 缺失；VLM `identity.model` 声明；基准报告一致性复核。
- **批准后动作**：小改动，随时可做。

### D8 — IndexTTS production 升级
- **状态**：代码级缺口已关（checksum 落地，gaps=0）；真实合成 Episode 8 3 句获 owner 声源批准 + bilibili ULA；admission 仍 research。
- **建议**：两条路任选——(a) 维持 research（当前 canonical 链可用，take 经人工 QC）；(b) 升 production：需人工标注 take 质量阈值（如 3 句 × 多 take 听感评分）+ 容量验收（CPU 吞吐 ~1–2min/句）。
- **批准后动作**：(b) 则建 take 质量标注 → 注册表 admission=production。

### D9 — FunASR/SenseVoice 模型卡许可 + 商用批准 + Speech 基准
- **状态**：paraformer-large 已真实运行（5 集基准）；模型卡许可未审（`MIT-code; model-card-governs-weights`）、commercial 未批准、checksum 未录（模型在 `NarratoPro/storage/models/funasr`，可实测 sha256）。
- **建议**：审查模型卡许可（ModelScope FunAudioLLM/SenseVoice + paraformer-zh）→ 批准商用 → 录 checksum → 正式 Speech 基准（CER 需 D5 参考文本；当前可交付段落/说话人/内容召回指标）。
- **批准后动作**：许可确认后录 checksum → `production_readiness_gaps(funasr)` 减项 → 以 5 集 SRT 建 CER/时间戳质量报告。

---

## 2. 建议决策顺序与依赖

```
D2（基线地位，零成本）→ D7（证据卫生）→ D3（容量目标）→ D4（VLM API 等价物）
→ D5（人工标注，影响 CER/mAP/阈值）→ D6（DET 类别，依赖 D5）→ D8/D9（TTS/ASR）
```
一次全批或分批均可；任一决策「暂缓/维持 research」都不阻塞当前 canonical 链（research 调用 + L1 人工 QC）。

## 3. 维持 research 时的运行边界（现状）
- Provider admission=research；`assert_production_ready` 只拦 production 声明，不拦 research 调用。
- 所有 AI 输出 confidence=unavailable、带 evidence、经 L1 checkpoint/人工 QC。
- Release Gate 3 永远人工；L2/L3 未授权。
