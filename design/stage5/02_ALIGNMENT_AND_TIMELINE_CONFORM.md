# Alignment and Timeline Conform

Version: 1.0

## 1. 目标

用真实 Voice 时长和字词对齐更新 Master Timeline，使镜头、解说、原声、字幕和包装重新同步，并把超出创意预算的问题送回受控 Reflow。

输入：VoiceTakeSelection、ApprovedTimelineIntentRef、NarrationLineSet、Alignment Provider、Platform Sync Profile。

输出：AlignmentArtifact、AlignmentQC、TimelineConformProposal、ReflowRequest、ConformedTimelineRef。

---

## 2. Alignment 流程

```text
Voice Technical Probe
→ ASR / Forced Alignment
→ Token-to-Line Mapping
→ Silence / Pause Segmentation
→ Alignment Quality Check
→ Actual Duration Delta
→ Timeline Conform Proposal
→ Local Reflow / Human Review
→ Conformed Timeline Commit
```

WhisperX 或其他 aligner 作为可替换 Provider。中文字符、词、标点和静音精度必须用项目样本评测；不能把 Provider timestamp 直接称为帧精确真相。

---

## 3. Alignment Contract

记录 line_id、audio range、word/character ranges、pause ranges、method、provider/model、ConfidenceRecord、unmatched tokens、estimated error 和 source VoiceRef。

若只获得句级时间，granularity 必须声明 sentence，不伪造字级时间。Alignment 低质量时字幕可以回退到句级 cue 并进入人工审核。

---

## 4. Conform 规则

Actual Duration Delta 分三类：

- within tolerance：更新 placeholder，不移动锁定结构；
- local adjustable：在当前 Beat 内调整 gap、pause、镜头 trim 或 narration entry；
- structural conflict：需要改 Narration、Beat 或目标时长，返回 Stage 4 Reflow/人工。

容差来自 Platform/Voice/Rhythm Profile。禁止通过任意速度拉伸、切字或覆盖对白消除 delta。

---

## 5. 原声与对白优先级

Conform 必须保护人工锁定原声、关键对白、动作点、Hook/Payoff anchor 和镜头最小可理解时长。Narration 与原声冲突时由 Mix/creative intent 决定错开、duck 或重写，不能简单同时叠放。

每次调整输出 before/after ranges、锁定项、违反风险和 dependency delta。

---

## 6. 并发与提交

Line alignment 并行；同一 Timeline 的 conform/reflow 串行提交。不同 Variant 并行。Alignment cache key 包含 Voice checksum、aligner/model/config 和语言 profile。

Conform 使用 expected Timeline version；stale proposal 必须 rebase 或拒绝。提交后失效 SubtitleCue、MixPlan、Preview/Render 等依赖。

---

## 7. 故障与降级

- Alignment unavailable：允许句级 Voice duration，但必须标低精度并转人工字幕审核。
- Token mismatch：生成 AlignmentConflict，不自动改 Narration 文本。
- 极端 duration delta：退回文本/Take/Stage 4，不强制 time-stretch。
- 人工调整 word boundary：创建 Correction 和新 Alignment version。

---

## 8. 测试与验收

- 漏字/多字、数字、标点、长停顿、快速语速和背景噪声。
- 句级/字级不同 granularity 的下游兼容。
- actual duration 回写后 Timeline 总时长、锁定点和依赖正确。
- stale conform、并发 Variant 和 Worker crash。
- 人工 boundary correction 可撤销。
- Subtitle、Mix 和 Render 不得读取旧 Timeline/Alignment 组合。

