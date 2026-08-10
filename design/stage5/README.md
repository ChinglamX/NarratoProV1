# Stage 5 — Production Audio, Subtitle and Rendering

Version: 1.0

## 1. 目标

把 Approved Timeline Intent 落实为可审核的真实 Voice、Alignment、Audio Mix、Subtitle/Graphics 和 Rendered Candidate，并用机器 QC、权利清单和人工 Release Review 保证同步、可懂度、画面与发布规格。

Stage 5 是创意意图进入媒体执行的汇合层。任何真实时长、布局或素材变化都必须回写新 Timeline version，不能在 FFmpeg 命令中暗中修正。

---

## 2. 媒体汇合拓扑

```text
Approved Timeline Intent + Profiles + Rights Registry
                         │
          ┌──────────────┼───────────────┐
          ▼              ▼               ▼
    TTS / Alignment   BGM / SFX       Subtitle / Graphics
          │              │               │
          └──── actual duration/layout ──┘
                         │
                Timeline Conform / Reflow
                         │
                    Mix Plan + ASS
                         │
                  Deterministic Render Plan
                         │
                Proxy → Final Candidate
                         │
             Technical QC + Rights Manifest
                         │
                         ▼
                Release Review Package
```

Temporal 编排媒体任务；FFmpeg/FFprobe 是执行与探测基线；ASS/libass 是服务端字幕基线。所有外部模型、音色、音乐、字体和特效资产通过 Provider/Asset Registry 接入。

---

## 3. 设计文件

- `01_TTS_PROVIDER_AND_VOICE_PRODUCTION.md`
- `02_ALIGNMENT_AND_TIMELINE_CONFORM.md`
- `03_AUDIO_ASSETS_AND_RIGHTS.md`
- `04_MIXING_DUCKING_AND_LOUDNESS.md`
- `05_SUBTITLE_GRAPHICS_AND_ASS.md`
- `06_RENDER_PLAN_AND_EXECUTION.md`
- `07_TECHNICAL_QC_AND_RELEASE_PACKAGE.md`
- `08_RESOURCE_EVALUATION_AND_FAILURES.md`
- `09_ACCEPTANCE_AND_BUILD_ORDER.md`

---

## 4. 输入

- ApprovedTimelineIntentRef、ApprovedCreativeBriefRef
- NarrationLineSet、original audio intent、Crop/Overlay intent
- Voice/Audio/Subtitle/Graphics/Platform Profiles
- 合法 Source、BGM、SFX、Font、Voice assets
- Resource/Cost/Automation Policy
- demo benchmark 与 Stage 4 Creative Quality Report

---

## 5. 输出

- VoiceAsset、VoiceTakeSelection、Pronunciation/Voice QC
- AlignmentArtifact 与 ConformedTimelineRef
- AudioAssetSelection、RightsManifest、MixPlan、MixedAudio
- SubtitleCueSet、ASS、GraphicsPlan、CollisionReport
- RenderPlan、ProxyRender、FinalCandidate
- TechnicalQCReport、ReleaseReviewPackage

---

## 6. 非目标

- 不重新决定 Story、Strategy 或核心创意方向。
- 不用时间拉伸掩盖明显不自然的 TTS。
- 不因 BGM 情绪强而牺牲对白/解说可懂度。
- 不默认使用无授权音色克隆、音乐、音效或字体。
- 不让 Preview 与 Final 使用两套独立时序/变换逻辑。
- 不自动执行 Release；Gate 3 始终由人决定。

---

## 7. 强制不变量

- TTS、Alignment、Subtitle、Mix、Render 都引用同一 Conformed Timeline version。
- TTS 实际时长变化必须通过 Timeline Patch/Reflow，而不是局部漂移。
- Rights unknown/restricted 的资产不能进入 Release Candidate。
- 音频目标来自版本化 Platform Profile，不把广播目标机械套到短视频平台。
- Subtitle/Graphics 使用确定性布局和相同字体资产，Preview/Final 一致。
- RenderPlan、FFmpeg build、codec/filter、font、asset checksum 全部可追踪。
- 正式输出原子提交；失败渲染不能注册为 Final Candidate。

---

## 8. 阶段验收摘要

- TTS 发音、完整性、自然度、音色和跨句一致性分别评测。
- Alignment、字幕和关键画面同步满足 Platform Profile。
- 人声可懂度、响度、True Peak、clipping 和异常静音通过机器与人工检查。
- 字幕不越界、不持续挡脸或关键物体，原片字幕处理无明显破坏。
- Proxy/Final 在时序、构图、字幕和混音语义上保持一致。
- Render 可恢复、幂等、缓存安全且所有资产权利已解决。
- Final Candidate 通过 demo/项目离线质量审核后进入人工 Gate 3。

完整构建与验收见 `09_ACCEPTANCE_AND_BUILD_ORDER.md`。

