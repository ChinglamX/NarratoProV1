# 多集 3–5 分钟成片流水线里程碑

Version: 1.0
Date: 2026-09-02
Direction: `PRODUCT_REDIRECTION.md` v2.0
Release Boundary: internal preview only

## 1. 当前结论

项目已经用两部真实多集短剧走通“剧情证据 → 营销命题 → 章节规划 → 跨集选镜 → 解说/TTS → 唯一 Master Timeline → 混音/字幕 → Render/QC”的纵向链路。

《海渊契约》最终修复候选获项目负责人 `useful`；该结论证明当前候选值得使用，不代表公开发布授权，也不外推为任意新剧已可完全无人干预生产。

当前权威候选：

- 海渊契约：`outputs/longform/haiyuan/final_preview_v4_narrationfix/haiyuan_longform_final_preview_v4_narrationfix.mp4`
- 山神印：`outputs/longform/shanshen_real/final_preview_v3_narrationfix/shanshen_longform_final_preview_v3_narrationfix.mp4`

## 2. 当前成片流程

```text
多集视频目录
  → Inventory / ffprobe / source hash
  → 逐集 ASR 与带时间码对白
  → ASR 窗口视觉抽帧与事件证据
  → SeriesStoryIndex（Goal / Conflict / Turn / Payoff / unresolved）
  → 2–3 个 Marketing Arc 与默认推荐
  → 6–9 章 ChapterBlueprint（时长、原声、解说预算）
  → 跨集 CandidateShot 与唯一镜头覆盖
  → canonical ClipCandidateSet / ClipSelectionPlan / MasterTimeline
  → 证据约束的解说草稿与预检
  → IndexTTS-2 真实语音
  → NarrationAnchor 按真实 WAV 时长重排
  → 原声 ducking、解说混音、ASS 中文字幕
  → 720×1280 H.264/AAC internal preview
  → TechnicalQC + A/V Sync + Narration Mix + Codex Review
  → 人工 useful / useful_with_revision / reject
```

## 3. 复用与新增

直接复用既有 Media/Story/Strategy/Timeline/E10/E11 能力，没有建立第二套 Timeline、FFmpeg、TTS 或字幕系统。

本阶段新增的薄层能力位于 `packages/longform`：

- `inventory.py`：多集素材清单与分组。
- `story_index.py` / `understanding.py`：整剧事件、证据、冲突链和 unresolved。
- `planning.py`：Marketing Arc、Hook 与 ChapterBlueprint。
- `clip_planning.py`：章节覆盖、唯一镜头选择和时长对账。
- `narration_planning.py`：事实、复述、证据和 TTS 预算预检。
- `canonical_adapter.py`：投影到既有 canonical Timeline contracts。
- `review.py`：长成片质量与连续性诊断。

运行入口保留为可恢复的分阶段脚本，便于复用已有产物而不重跑 ASR/TTS：

- `scripts/longform_pipeline.py`
- `scripts/build_longform_evidence_pack.py`
- `scripts/promote_longform_story_index.py`
- `scripts/build_longform_shot_candidates.py`
- `scripts/build_longform_canonical_preview.py`
- `scripts/synthesize_longform_narration.py`
- `scripts/build_longform_narration_anchors.py`
- `scripts/render_longform_final_preview.py`
- `scripts/accept_longform.py`

## 4. 已验证结果

### 海渊契约

- 22 集、1,722.1 秒完成媒体清单和 ASR。
- 当前正式事件链覆盖第 1–8 集的 14 个双证据事件。
- 3 个 Arc、8 章、299 个候选镜头、140 个最终时间线片段。
- 14 条 IndexTTS-2 解说，合计 52.837 秒。
- 最终视频/音频均为 240.000 秒，6000 帧。
- 14 个解说窗口与最终混音相关度 0.706–0.976。
- -14.9 LUFS、-1.5 dBTP；全部 TechnicalQC passed。
- 项目负责人结论：`useful`。

### 山神印

- 20 集完成 inventory；正式成片主线使用第 1–6 集的 16 个双证据事件。
- 13 条 IndexTTS-2 解说，合计 46.382 秒。
- 最终视频/音频均为 240.000 秒，6000 帧。
- 13 个解说窗口与最终混音相关度 0.645–0.974。
- -13.7 LUFS、-1.5 dBTP；全部 TechnicalQC passed。
- 当前最新修复版仍待项目负责人完整内容结论。

## 5. 关键缺陷与已固化防线

- 选镜评分曾直接改变时间顺序：现按章节因果与源时间组装。
- 短镜头曾产生小于 0.5 秒闪帧：现 fail closed。
- 每镜 25fps 量化曾累计造成最高约 280ms 音画漂移：现按全局帧边界分配，PCM 整轨拼接，并加入一帧容差 A/V Sync blocker。
- 解说音轨曾只参与 sidechain、没有进入最终 amix：现显式 `asplit`，并以逐窗口 aligned-vs-mixed 相关度作为 Narration Mix blocker。
- loudnorm 曾缩短尾部：现独立 PCM pad 到目标时长。
- libass/CJK 字体、字幕换行、响度和 True Peak 已加入真实渲染验证。

## 6. 人机边界

AI/工具负责证据整理、候选命题、章节/镜头/解说建议、TTS、时间线、渲染和机器 QC。Codex 作为 Review Director 审核和有限润色，不以自身评分替代人类内容结论。

人仍负责：营销方向高成本选择、重大剧情判断、最终内容效果和所有 Release 决策。当前素材仅登记为内部分析/测试用途，禁止公开发布。

## 7. 尚未完成

- 《海渊契约》虽已转录 22 集，正式事件索引仍主要覆盖第 1–8 集；尚未证明第 9–22 集没有更强营销闭环。
- 尚未用第三部 held-out 剧集证明固定入口的低干预重复生产。
- 多个恢复脚本尚未收敛为一个面向个人创作者的单命令入口。
- BGM/SFX、正式 Rights Manifest、线上表现和 L2/L3 自动化不在本里程碑范围。

## 8. 下一阶段

下一阶段不扩建平台。先补齐《海渊契约》第 9–22 集事件与视觉高光覆盖，生成一个“后期奇观优先”的 Challenger，与当前 `useful` 因果完整版做 A/B；随后用《神龟有灵》验证第三部 held-out 固定入口。
