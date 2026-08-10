# Audio Assets and Rights

Version: 1.0

## 1. 目标

建立可检索、可裁切、可循环、权利明确的 BGM/SFX/ambience 资产库，并为 Timeline Beat 提供受控候选和选择依据。

输入：ConformedTimelineRef、Audio Intent、Beat/Rhythm Curve、Audio Asset Registry、Rights/Brand Profile。

输出：AudioAssetCandidateSet、AudioAssetSelection、Edit/Loop Plan、RightsManifestDelta、AudioRiskReport。

---

## 2. Asset Registry

每个资产记录：checksum、版本、来源、作者/供应方、license 文本/证据、使用地域/平台/期限、商业/修改/同步许可、署名要求、Content ID 风险、撤销状态、音频技术属性和语义标签。

Rights unknown、范围不匹配、过期或 revoked 的资产只能出现在 research/review 候选，不能进入 Release Candidate。

字体、音色和视频素材在统一 Rights Manifest 汇总，但本文件聚焦音频资产。

---

## 3. 音频分析与索引

使用 FFprobe/FFmpeg 和合规音频分析工具提取 duration、sample rate、channels、loudness、true peak、tempo/beat candidate、key、energy curve、loop points 和静音。

Embedding/标签用于情绪、乐器、速度和场景召回；它们不证明权利，也不决定最终适配。所有自动标签保留 provider/version/confidence。

---

## 4. BGM 检索与结构适配

检索同时考虑：情绪曲线、Beat 结构、tempo/energy、开场响应、build/drop/ending、原声/解说空间、可循环性、长度、类型软偏好和权利。

选择输出多个受限候选以及为何适合/不适合。Timeline 结构优先；禁止为了卡音乐强行破坏剧情节奏。

Edit/Loop Plan 明确 source ranges、crossfade、loop seam、beat alignment intent 和 ending handling。Stage 5 只使用可复现编辑参数。

---

## 5. SFX 与 Accent

SFX 用于强调真实动作、转场、Hook 或包装，不用于掩盖内容薄弱。每个 SFX 绑定 Timeline event/intent、强度、频段风险和 rights。

限制连续密度、重复次数和与对白冲突。夸张音效不得制造原剧情不存在的事实含义。

---

## 6. 并发、缓存与人工选择

BGM/SFX 候选检索可与 TTS 并行；选择在 Conformed Timeline 后确认。分析/embedding 按资产 checksum 缓存。不同 Variant 可共享候选，但 Selection Artifact 独立。

人工可以 pin/ban/replace、调整 loop/entry/exit，并记录理由。权利状态变化使所有引用 Release Candidate 立即 rights_blocked。

---

## 7. 测试与验收

- license scope、到期、撤销、署名和 Content ID 风险。
- 相同音频不同文件名的 checksum 去重。
- loop seam、crossfade、短曲延长、长曲裁切和 ending。
- BGM 情绪适合但与人声频段冲突时不能仅凭语义高分选中。
- 音效密度和重复风险可定位。
- 所有最终选择能生成完整 Rights Manifest 链路。

