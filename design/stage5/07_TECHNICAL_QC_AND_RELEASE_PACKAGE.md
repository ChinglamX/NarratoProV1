# Technical QC and Release Package

Version: 1.0

## 1. 目标

对 Rendered Candidate 执行可定位、可复现的技术与权利检查，并把成片、报告和全部版本组织成 Gate 3 可审核的 Release Review Package。

输入：FinalCandidate、RenderPlan/Execution Report、ConformedTimeline、Mix/Subtitle/Graphics artifacts、Platform Profile、Rights Registry。

输出：TechnicalQCReport、RightsManifest、OfflineQualityInputs、ReleaseReviewPackage、BlockerSet。

---

## 2. Technical QC 分层

### Container/Stream

使用 FFprobe 验证容器、codec、profile、分辨率、显示比例、帧率策略、duration、音频 codec/sample rate/channels、stream start 和可解码性。

### Timeline/Sync

对账 expected/actual duration、frame count、首尾、audio/video offset、Narration Alignment、Subtitle Cue 和关键事件同步。阈值来自 Platform Profile。

### Video

检测黑帧、冻结、损坏帧、异常闪烁、crop 越界、明显色彩/缩放错误、关键主体覆盖和字幕/graphics 抽帧。

### Audio

检测 integrated/short-term loudness、true peak、clipping、异常静音、声道/采样率、解说/对白可懂度风险和首尾截断。

### Subtitle/Graphics

检查缺字、越界、安全区、持续遮脸/关键物体、cue overlap、阅读速度、同步和服务端实际渲染抽帧。

---

## 3. Blocker 与严重度

Blocker 至少包括：文件损坏/规格不符、明显音画字幕不同步、关键语言不可辨、clipping/异常静音影响理解、缺字、持续遮挡关键内容、权利未解决。

每个问题包含 time range/frame、metric/raw evidence、Profile rule、severity、affected artifact 和 required fix。总分不能抵消 blocker。

检测器 unavailable 时对应检查不能标 Pass，只能 unavailable 并按 Policy 转人工。

---

## 4. Rights Manifest

汇总 Source video、BGM、SFX、Voice/voice reference、Font、Image/Graphic、Model-generated asset 的 asset/version/checksum、来源、license、授权范围、期限、署名、限制和检查时间。

Manifest 固定的是 Release Candidate 当时的 rights snapshot。后续撤销触发发布风险事件和候选状态更新，但不删除原审计记录。

---

## 5. Release Review Package

包含：

- Final/Proxy media 与 checksum；
- project/run/variant 和所有 Story/Strategy/Timeline versions；
- Voice/Alignment/Mix/Subtitle/Render/QC artifacts；
- Quality Standard 分维度输入与 demo comparison；
- blockers、warnings、accepted risks；
- Rights Manifest、成本、模型/配置/工具版本；
- 问题时间码和可执行 Correction 入口。

Package 只准备 Gate 3，不自动发布。Gate 3 始终由人执行 Release/Revise/Reject。

---

## 6. QC 执行与并发

独立技术检查可并行；最终 Verdict 在全部 required checks 汇合后确定。长视频可按窗口分析，但首尾、全局 loudness、duration 和跨段同步必须全局检查。

QC cache key 包含 Final checksum、detector/tool/Profile versions。Candidate 字节变化必须重新执行相关检查。

---

## 7. 修正路由

- TTS 发音/漏字 → Voice/Narration Correction。
- Alignment/字幕同步 → Alignment/Subtitle。
- BGM 盖声/削波 → MixPlan。
- 字幕遮挡/缺字 → Layout/Font。
- crop/镜头问题 → Stage 4 Timeline Patch。
- 编码/规格 → Render Profile/Plan。
- rights → Asset replacement/authorization，不允许人工“忽略通过”。

修正后生成新 Candidate 和 QC Report，旧报告不可复用为通过依据。

---

## 8. 测试与验收

- 对每类 blocker 注入固定 faulty media。
- detector unavailable 不得产生假 Pass。
- 分块检查与全局检查边界一致。
- 字节变化使 QC cache 正确失效。
- Rights revoked/expired/unknown 阻断 Gate 3。
- Release Package 可由独立 Review Director 完整复核且引用均可打开。

