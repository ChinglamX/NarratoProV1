# Resource, Evaluation and Failures

Version: 1.0

## 1. 目标

建立 Stage 5 的资源调度、质量评测、成本、失败恢复和自动化边界，使媒体生产在个人机器和多 Worker 环境中稳定运行。

输入：Stage 5 Workflows、Provider/Asset Catalog、Resource Profile、Evaluation Dataset、Quality/Platform Profile。

输出：CapacityReport、Stage5Benchmark、CostReport、FailureReport、AutomationSafetyReport、Runbooks。

---

## 2. Task Queue

| Queue | 工作 | 核心资源 |
|---|---|---|
| tts_local | 本地 TTS | GPU/Metal/RAM/model residency |
| tts_cloud | 云端 TTS | rate/cost/data policy |
| alignment | ASR/forced alignment | CPU/GPU/model |
| audio_cpu | analysis/mix/loudness | CPU/RAM/disk |
| subtitle_cpu | cue/layout/ASS | CPU/font/assets |
| preview_render | 代理渲染 | encoder/disk/latency |
| final_render | 正式渲染 | encoder/CPU/RAM/disk/thermal |
| technical_qc | probe/video/audio/layout checks | CPU/IO/global barriers |

TTS、音频资产检索和初步字幕可并行；必须在实际 Alignment/Conformed Timeline 汇合后才能提交最终 Cue、Mix 和 Render。

---

## 3. Admission 与背压

ResourceRequest 声明 CPU、RAM、VRAM/Metal、model key、encoder session、temporary/final disk、预计网络/成本和优先级。

Admission 检查磁盘 low/high watermark、统一内存争用、FFmpeg 内外线程、VideoToolbox session、热状态、云端预算/限流和 Project fairness。

交互 Preview 有受限优先级，Final Render 保留最低资源份额。无法满足资源时排队而不是先启动后 OOM/磁盘满。

---

## 4. 分层评测

TTS：字/词错误、关键词/数字/否定、自然度、音色一致、情绪/停顿、duration error、吞吐/成本。

Alignment：token coverage、timestamp deviation、unmatched、granularity、人工 correction rate。

Audio：可懂度、ducking artifact、loudness/true peak、clipping、静音、人工听感。

Subtitle：断句、阅读速度、同步、layout collision、缺字、位置稳定、golden frame。

Render/QC：规格、帧/时长、proxy/final parity、crash/retry/cache、blocker precision/recall。

Craft Quality 和技术正确性分开报告；机器 QC 通过不代表 demo 级成片质量。

---

## 5. 故障矩阵

- TTS Provider unavailable/timeout/OOM/quality reject → retry、准入回退或人工，保留 provenance。
- Alignment low quality → sentence-level/manual，不伪造 word timing。
- Audio asset rights change → rights_blocked，停止 Release。
- Mix/ASS compile error → non-retryable config 或修正后新版本。
- FFmpeg crash/cancel/disk full/hardware encoder error → staging cleanup、segment reuse、approved fallback。
- QC detector unavailable → unavailable/fail closed，不假 Pass。
- Artifact/version stale → 阻止汇合和 Final 注册。

所有失败使用 Stage 1 Error Envelope、heartbeat、idempotency 和 Reconciler。

---

## 6. 自动化潜力与边界

可逐步达到 L3 的低风险能力：技术 probe、checksum、规格、响度/peak、缺字、边界、安全区、缓存/重试和部分同步检查，前提是校准严重漏检率并持续抽样。

保持人工：声音表演、BGM 情绪与动态、细微同步观感、字幕审美、完整成片质量和 Release Gate。

高置信度不能覆盖 rights、不可懂人声、明显不同步或文件损坏 blocker。

---

## 7. 成本与可观测性

记录每句 TTS、每分钟 alignment/mix/render/QC、候选 Take、云端费用、失败重试、cache hit 和人工修正成本。

Trace：Timeline → Voice/Alignment → Conform → Audio/Subtitle → Render → QC → Release Package。

Metrics：queue/runtime、model/encoder utilization、peak memory/disk、TTS reject、alignment correction、subtitle collision、render failure、QC blocker、rights block、candidate cost。

---

## 8. 性能与故障测试

覆盖长解说、多 Variant、复杂 ASS、多字体、大量 SFX、4K/HEVC 源、并发 Preview/Final、Mac 热限制、磁盘高水位和 Worker kill。

报告 P50/P95、吞吐、峰值资源、每分钟成片成本、缓存收益、恢复时间和质量变化。资源/速度优化不能跳过相同 Quality Profile 对比。

---

## 9. 发布、灰度与回滚

TTS/Alignment Provider、Pronunciation、Mix/Subtitles Profile、字体包、Render Compiler、FFmpeg/libass build 均按版本发布：shadow/golden regression → canary Variant → staged rollout → production。

回滚必须：

- 恢复完整版本集合，而不是只替换单个容器；
- 创建新 Run/Artifact，不覆盖已经生成的 Voice、Mix、ASS 或 Final Candidate；
- 重新执行受影响的 Alignment、Conform、QC 和 Rights Preflight；
- 保留 canary/rollback 原因、质量差异、tool/model/font checksums；
- 验证旧 Worker 能读取当前 Contract 和历史 Timeline。

Rights revoked/expired 不允许通过回滚旧 Registry snapshot 恢复发布资格。此类情况只能取得新授权或替换资产后重新生产和审核。

---

## 10. 测试与验收

- 所有 typed failure 有明确 retry/fallback/manual/fail closed 行为。
- 多 Variant 并发不混用 Voice、Alignment、Mix、Subtitle 或 Render artifacts。
- 自动 QC 的 blocker 漏检率按故障集评测。
- Resource Profile 可阻止 OOM/ENOSPC 并保持项目公平。
- 性能优化前后质量和 rights 结果一致。
- 历史 Run 可用原 Provider/Profile/FFmpeg/font versions 重放或明确说明不可字节复现范围。
