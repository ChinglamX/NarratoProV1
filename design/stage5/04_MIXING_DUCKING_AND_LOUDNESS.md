# Mixing, Ducking and Loudness

Version: 1.0

## 1. 目标

把原声/对白、解说、BGM、SFX 和 ambience 编译为可复现 MixPlan，优先保证语言可懂度，同时维持动态、情绪和平台适配。

输入：ConformedTimelineRef、VoiceAsset、original audio、AudioAssetSelection、Audio/Platform Profile。

输出：MixPlan、FFmpeg Audio Graph、MixedAudioAsset、Loudness/Intelligibility Report、AudioRisk。

---

## 2. 工具与边界

FFmpeg filtergraph 作为执行基线：trim/adelay/afade、aresample、equalizer、compressor、sidechaincompress、amix、loudnorm/ebur128、limiter 等。滤镜支持和行为绑定 FFmpeg build/version。

响度测量参考 ITU-R BS.1770/EBU R128 方法；最终 integrated/short-term loudness、loudness range 和 true peak 目标由 Platform Profile 定义，不写死广播数值。

MixPlan 是业务真相；filtergraph 是编译产物。

---

## 3. MixPlan

记录每轨 source、timeline range、gain envelope、fade、EQ/dynamics、pan/channel mapping、ducking relation、limiter、measurement profile 和 automation points。

优先级通常为关键对白/解说可懂度 → 必需原声 → BGM → SFX，但具体片段由 Creative Intent 配置。无对白的动作/情绪段可以让原声或音乐成为主轨。

禁止全片用一个固定音量比例。

---

## 4. Ducking

Ducking 使用 narration/dialogue 活跃区间、look-ahead、attack、release、depth 和频段策略生成包络。目标是自然让位，不产生抽吸、突降或句间频繁跳动。

原声对白与解说重叠必须有显式 intent：preserve、duck、mute、alternate 或 manual。系统不得默认同时保留造成听不清。

SFX 在人声附近设置峰值和频段风险限制。

---

## 5. Loudness 与技术处理

采用分析 → 渲染 → 复测流程：

1. 分轨测量和异常检测。
2. 编译 MixPlan 与必要 dynamics。
3. 输出高精度中间音频。
4. 测量 integrated/short-term、LRA、true peak、clipping、DC、silence。
5. 不达标时修改 MixPlan 后重渲染，而不是只改报告。

响度达标不代表可懂度达标；还需语音区间的相对能量、频段遮蔽指标和人工耳听。

---

## 6. 并发与缓存

分轨 probe/analysis 并行；局部 envelope/EQ suggestion 可并行。最终 mix 和全片 loudness 必须在 Conformed Timeline 汇合后执行。

缓存按 TimelineRef、全部 audio checksums、MixPlan、FFmpeg build 和 output profile。任何源音频或 envelope 变化都失效 MixedAudio/Render。

不同 Variant 并行受 CPU、磁盘和 encoder admission 控制。

---

## 7. 人工修正

Workspace 支持 gain keyframe、duck depth、fade、BGM entry/loop、SFX timing 和 track solo/mute。编辑生成 MixPlan Patch，不直接修改最终 wav。

完整试听至少使用目标设备类型和普通音量，避免只看波形/仪表。接受超出软目标的创意片段需记录范围和理由；clipping、不可辨人声等 blocker 不可豁免。

---

## 8. 测试与验收

- 解说+对白、喊叫、低声、密集 SFX、强低频 BGM 和静音段。
- Ducking attack/release、句间 pumping 和首尾截断。
- integrated/short-term/true peak 复测与 profile 边界。
- 多声道/单声道、采样率转换和相位/声道映射。
- 音频改变后 Render 失效。
- 机器指标与人工可懂度审核分别记录且均通过。

