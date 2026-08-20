# 项目负责人审阅清单（2026-08-19，State v111）

本清单汇总当前需要项目负责人裁决/审阅的全部事项。每项给出：看什么、怎么判断、怎么回复。回复方式任选：直接说结论（如「LLM 草稿采纳 L1+L2，L3 改为…」），或告诉我「按清单 A/B/C 逐项给结论」。

---

## A. LLM 解说草稿审阅（创作边界，3 句）

- **打开**：`outputs/vc003_episode_08/narration_drafts/narration_drafts_card.md`
- **对照基准**：当前已批准成片 `outputs/vc003_episode_08/audio/canonical_e11.mp4`（26s，人工批准解说）
- **判断问题**：
  1. 每句草稿是否准确描述对应情节（不夸大、不虚构）？
  2. 是否有证据外暗示？（示例：L2「暗线交易悄然落定」的「暗线」是剧情里没有的信息；L3「致命的后手」是营销化推演——这类语义漂移机械规则抓不到，需要你判断）
  3. 三句连起来是否构成流畅的「威胁→交易→卡密」解说？
- **可给结论**：`采纳全部` / `逐句改`（贴出修改后文本）/ `不采纳`（维持 Agent 起草）

## B. 自动选镜 Timeline 草稿审阅（L1 checkpoint）

- **打开**：预览视频 `tmp/vc003-e08-eefec351-cc41-441b-8844-0ba0cdafc9b9-preview.mp4`（20.33s；用访达双击 / QuickTime 播放）
- **对照基准**：已批准 Timeline 预览 `tmp/vc003-e08-d3690d71-444a-43d9-bbd0-52bd1c91d371-preview.mp4`（26s，人工窗口）
- **背景**：本草稿的三个镜头窗口**完全由机器自动选出**（真实 ASR 证据窗口 41.07–49.29 / 16.09–26.24 / 28.59–30.53s，无人工选窗），解说仍为人工批准句
- **判断问题**：自动选出的镜头是否值得继续？和人工选窗版本相比如何（20.3s vs 26s，威胁段 41–49s 开头）
- **可给结论**：`approve`（批准） / `revise`（说明改哪） / `reject`；批准命令：
  `.venv/bin/python scripts/produce_vc003_timeline.py --run-id eefec351-cc41-441b-8844-0ba0cdafc9b9 --decision approve`

## C. 形式化准入决策（D2–D9，ADR-032 需你批准）

- **打开**：`evaluation/reports/ADMISSION_DECISION_PACKAGE.md`（每项含：现状 / 建议 / 批准后动作 / 依赖顺序）
- **快速版**（可只选要批的）：
  - **D2** 接受 benchmark v1/enriched 为工程基线（零成本）
  - **D5** 授权人工标注 frozen_test 子集（OCR 参考文本/DET 参考框/VLM rubric）→ 之后才能算 CER/mAP/阈值
  - **D8** IndexTTS 维持 research 或升 production（代码级缺口已关，升需 take 质量阈值标注）
  - **D9** 审查 FunASR/SenseVoice 模型卡许可 + 商用批准 + 录 checksum
- **可给结论**：如「批准 D2、D5、D9；D8 维持 research；其余暂缓」

## D.（可选了解）自动选镜机制证据

- 三集跨集验证：`evaluation/evidence/ep2_m5_windows_asr_validation.md`、`ep7_heldout_window_asr_validation.md`（ASR 窗口与事件窗口 6/6、4/4 对齐）
- 自动选镜细节：`outputs/vc003_episode_08/vlm_candidates/vlm_candidates_card.md`、`asr_evidence/asr_evidence_card.md`

---

## 回复后我会做什么

| 你回复 | 我执行 |
|---|---|
| A 采纳/修改 | 更新解说 →（如需）重跑 E10 候选 |
| B approve/revise | 签署 workflow（approve）或按意见重跑 |
| C 批准若干 D 项 | 执行对应升级动作（标注基线、checksum 录入、许可审查推进等） |
| 全部暂缓 | 停止该目标，保留现状与证据 |
