# 项目差距评估（距端到端自动化生产）

Date: 2026-08-19（State v107 更新；替代 2026-08-16 版本）
依据：PRODUCT_CONTROL_SYSTEM.md、PRODUCT_CONTROL_BOARD.md（2026-08-19 审计）、PROJECT_STATE v107、evaluation/qualification/e06_g05.json / e07_h06.json / e08_i05.json / e09_j06.json / e10_k06.json / e11_l06.json、E06_ADMISSION_UPGRADE_ASSESSMENT.md、本次会话真实执行证据（Episode 8 Gate 1→2→E09→E10→E11 全链 + 人工验收 useful）

## 1. 说明：进展更新

- **E10/E11 canonical 全链真实闭环**：IndexTTS-2 真实配音 → conform → 混音 → ASS → Docker libass 渲染 → TechnicalQC passed；Episode 8（26s，威胁倒叙）获 `useful`（State v97–v99）。
- **真实 approved 输入链首次贯通**：Gate 1 → Gate 2 → E09 Timeline（人工 checkpoint）→ E10/E11 canonical → 人工验收。
- **J05 DB 级 timeline review 集成**：`approved_timeline_intent` pointer 发布（State v100）。
- **自动内容生成（research）已实现并验证（State v102–v107）**：VLM 自动选镜（raw 选窗 → evidence 精修 → 真实 FunASR ASR 证据窗口驱动）已跑通「自动选镜 → E09 Timeline 草稿」（run `eefec351…` 20.33s 到达人工 checkpoint，无人选窗）；LLM 解说草稿生成（规则校验通过，3 句）；真实 Speech 基准 5 集（paraformer-large 定时 ASR + 说话人分离，SRT 落 `evaluation/evidence/speech_baseline/`）。
- **准入取证推进**：IndexTTS-2 权重 checksum 已落地（`production_readiness_gaps`=0，admission 仍 research）；FunASR 已登记候选 Provider；E06 评估刷新（D1 已决，D8/D9 新增）。

## 2. 目标形态与完成度（量级估计，非项目正式单一指标）

| 目标形态 | 完成度估计 | 剩余主要工作 |
|---|---|---|
| **最小生产闭环**（一部成片，真实数据，人工只过 3 个正式 Gate + Release） | ≈ 80%+ | 形式化准入决策（D2–D9）、完整 rights manifest、正式 QC 套件/parity、M5 统一入口正式验证、一次真实 Release Gate 3 |
| **规模化高质量生产**（多集/多剧、Enhancer 全量、容量/成本） | ≈ 50%+ | 自动选镜/解说从 research 升 production（依赖准入决策）、真实跨集 Identity/Story corpus、容量/成本验收 |
| **全自动无人值守（L2/L3 自动路由）** | ≈ 10–15% | Confidence 校准（真实 Gold/Baseline）、反馈闭环、漂移监控；需显式授权 |

项目治理明确反对单一百分比（PRODUCT_CONTROL_SYSTEM.md §3），以上仅量级参考。

## 3. 核心链路完成度（Media → … → Release）

```
Media ✅ → Observation 🟡 → Fact/Story 🟡 → Strategy 🟢 → Timeline 🟢
→ Voice/Audio/Subtitle 🟢 → Render/QC 🟢 → Quality 🟡 → Release ⬜(永远人工)
```

## 4. 六阶段工程 vs 生产验收

| Stage | 工程实现 | 生产验收 | 关键缺口 |
|---|---|---|---|
| S1 Production Foundation（E00–E05） | ✅ 100% | ✅ 签收 | CI Postgres（5 DB 测试 CI 跳过）、Python resolution lock |
| S2 Drama Intelligence（E06/E07） | ✅ 工程（观察/身份/Fact/Story 实现） | ❌ 0% | **Provider 生产准入**（OCR/Det/VLM/TTS/ASR 均 research）；Speech 基准缺；跨集 Identity/Story 真实语料验收缺 |
| S3 Marketing Intelligence（E08） | ✅ 100%（strategy/hook/Gate2） | 🟡 Gate 2 已真实执行 1 次（Episode 8） | Hook 真实效果数据缺（吸引力 unavailable）；人工一致性阈值未建 |
| S4 Creative Timeline（E09） | ✅ 100%（真实 preview、人工 checkpoint、replay） | 🟡 Episode 8 已真实批准 1 次 | **自动选镜/自动视觉事件**缺（候选集现由 Agent/人构建，依赖 VLM admission）；craft 评分签核 pending |
| S5 Audio/Subtitle/Render（E10/E11） | ✅ 真实闭环（IndexTTS→conform→mix→ASS→libass→QC） | 🟡 2 个 real-data 候选获 `useful` | BGM/SFX rights；TTS CPU 吞吐；正式 QC 套件（黑帧/静音/字幕几何）、proxy/final parity、fault/capacity drills；完整 rights manifest |
| S6 Quality Automation | 🟡 设计 ~30% | ❌ 0% | **自动解说文本生成**（NarrationSourcePort 现为 L1 人工 line set）；Calibration 真实 Gold/Baseline→Confidence；L2/L3 |

## 5. 剩余缺口按优先级

### A. 生产资格层（形式化准入；最优先，纯工程+决策）
1. **E06 Provider admission 升级**（OCR/Det/VLM/IndexTTS/FunASR → production）：有真实 benchmark v1/Episode 8 证据；缺人工标注基线（CER/mAP/claim 对照）、阈值（Quality Profile）、（VLM）API 准入等价物、（TTS/ASR）权重 checksum 与模型卡。D1 commercial 批准已 3/3（2026-08-16）；IndexTTS 权重 checksum 可立即补（文件已 pin 在 INDEXTTS_HOME）。
2. **E06 Speech 基准**：真实短剧 ASR 语料 + FunASR 模型商用批准（当前仅 research adapter，未登记注册表）。
3. **E07/E08 真实 corpus 生产验收**：跨集身份（IdentityGraph 有实现无真实 corpus）、Story 严重错误阈值、Hook 数据。

### B. 内容自动生成层（research 已验证，升 production 依赖 A）
4. **自动视觉事件/选镜**：**research 已实现并验证**（`packages/intelligence/vlm_clip_retrieval.py` + FunASR ASR 证据窗口 → 自动 ClipCandidate → Timeline 草稿 `eefec351…`）；production 化依赖 VLM/ASR 准入决策。**发现**：对白驱动事件需 ASR 证据窗口为主驱动（单帧画面相关性召回有限）。
5. **自动解说文本**：**research 已实现并验证**（`narration_draft.py` 规则校验 + Ark LLM 草稿生成，3 句全过）；升 production 需 admitted LLM + L1 审核边界确认（草稿审阅挂起）。
6. **Hook 吸引力校准**：真实曝光/留存数据 → 候选可排序。

### C. 闭环收尾（工程量小、价值直接）
7. E11 完整 QC 套件 + proxy/final parity + fault/capacity drills。
8. E09 craft 评分人工签核（AI 草稿已归档待签）。
9. M5 单一非开发者入口在 approved 链路正式验证（对齐 PERSONAL_CUT_GUIDE）。
10. 一次真实 Release Gate 3 执行（需发布场景 + 完整 rights manifest）。

### D. 规模化层（明确不在当前主线）
11. Calibration Program 真实 Gold/Baseline → Confidence calibrated → L2/L3 可行性。
12. 容量/并发/成本（IndexTTS CPU 慢、磁盘、CI）。

## 6. 永远人工的边界（治理设计，不是缺口）
- **Gate 2 策略方向选择**：ADR-042 固定 L1 人类；候选生成可自动化，选择永不自动。
- **Release Gate 3**：永远 human release_approver（代码层 fail-closed）。
- 重大剧情/营销判断、素材权利人工兜底。

## 7. 建议推进顺序
A. **回填可立即取证的准入证据**（IndexTTS 权重 checksum、FunASR 登记与模型卡）→ 更新注册表与准入评估 → 提交 D2–D7 决策包给项目负责人。
B. 与 A 并行：**自动 Clip 候选生成**设计（VLM production 后：Story 事件 + 证据 → 语义检索生成候选；现 PersistenceClipIndex 仅读人工 approved 候选集）。
C. **自动解说生成**设计（admitted LLM + L1 审核边界，替代 Agent 起草）。
D. E07/E08 真实 corpus 生产验收（依赖 A 的 identity/detection admission）。
E. E11 完整 QC/parity + M5 统一入口验证。

## 8. 一句话
**「能出成片的端到端生产链」已真实跑通（≈80%）**——最大缺口（E10/E11 + 真实 approved 输入链）已闭环；剩余核心是①形式化准入（Provider/语料）与②自动内容生成（VLM 选镜、LLM 解说），二者决定从「Agent 辅助 + 人工 Gate」升级到「机器自动产出草稿、人只做裁决」。全自动无人值守（L2/L3）依赖校准数据与显式授权，量级上仍有大半路程。
