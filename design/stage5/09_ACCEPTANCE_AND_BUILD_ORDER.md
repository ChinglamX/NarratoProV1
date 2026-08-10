# Stage 5 Acceptance and Build Order

Version: 1.0

## 1. 目标与契约

目标：规定生产声音、字幕、渲染和 Technical QC 的依赖顺序、退出条件、故障演练、回滚及 Gate 3 交接标准。

输入：Stage 1–4 已批准能力、Stage 5 设计、Provider/Asset Registry、Evaluation Dataset、Platform/Quality/Resource Profiles 和测试环境。

输出：Milestone Evidence、Stage5 Acceptance Report、Capacity/Cost Baseline、Rights/QC Evidence、Rollback Record、Release Review Readiness。

---

## 2. 构建顺序

### Milestone 1 — Media Production Contracts

- Voice/Take/Alignment/Mix/Subtitle/Graphics/Render/QC/Rights schemas
- Provider/Asset Registry、Profile 与 dependency rules
- Stage 4 placeholder → Stage 5 formal artifact migration

退出：Schema、版本、Rights、失效和兼容测试通过。

### Milestone 2 — TTS and Voice QC

- Provider Gateway、normalization、pronunciation
- Take generation/selection、technical/ASR/human QC
- voice rights、budget、fallback

退出：分层发音/完整性/自然度/一致性 benchmark 和失败路径通过。

### Milestone 3 — Alignment and Conform

- forced alignment、granularity/confidence
- actual duration delta、local conform、Stage 4 reflow route

退出：同步、锁定项、stale 防护和依赖失效通过。

### Milestone 4 — Audio Assets and Mix

- BGM/SFX registry/retrieval/rights/edit plan
- MixPlan、ducking、loudness/true peak/intelligibility

退出：权利、可懂度、动态、机器指标和人工试听通过。

### Milestone 5 — Subtitle and Graphics

- semantic segmentation、alignment timing、layout solver
- ASS/libass、font registry、collision/golden frames

退出：同步、阅读、安全区、遮挡、缺字、稳定性和渲染一致通过。

### Milestone 6 — Render Execution

- RenderPlan/compiler/preflight
- proxy/final、segment cache、retry/fallback、atomic commit

退出：parity、crash/retry/cache、资源和安全测试通过。

### Milestone 7 — Technical QC and Release Package

- stream/sync/video/audio/subtitle QC
- Rights Manifest、blocker routing、Release Package

退出：故障集 blocker 检出、不可用 fail closed 和独立复核通过。

### Milestone 8 — Production Qualification

- demo/项目完整成片评测
- capacity/cost、failure injection、dashboard/runbooks
- provider/compiler/profile rollback rehearsal

退出：固定输入和 Resource Profile 下质量、恢复、成本、权利与 Gate 3 readiness 获批准。

---

## 3. 验收矩阵

| 维度 | 必须证明 |
|---|---|
| Voice | 发音、完整性、自然度、音色/情绪一致、rights |
| Alignment | granularity、误差、实际时长回写、低质量降级 |
| Audio | 资产权利、BGM/SFX 适配、人声可懂、ducking、响度/peak |
| Subtitle | 断句、阅读、同步、safe area、碰撞、缺字、稳定 |
| Graphics | 内容批准、模板、字体/图片 rights、Preview/Final parity |
| Render | deterministic plan、preflight、cache、retry、atomic commit |
| QC | blocker 定位、unavailable fail closed、Profile 版本 |
| Rights | 每个外部资产来源、范围、期限和撤销状态 |
| Incremental | Voice/Timeline/Style/Mix 改动精准失效 |
| Review | 完整成片、demo 比较、Release Package、Gate 3 人工 |
| Operations | 并发、资源、成本、trace、runbook、rollback |

---

## 4. 端到端验收场景

1. 读取 ApprovedTimelineIntentRef 和所有 Profile/Rights。
2. 并行生成 TTS Takes、BGM/SFX candidates 和字幕初稿。
3. 注入人名误读、漏字、时长超限、音色漂移和 Provider OOM。
4. 选择 Voice、对齐并回写 Timeline，验证局部/结构 Reflow。
5. 选择合法音频资产，生成 MixPlan、ASS 和 GraphicsPlan。
6. 注入 BGM 盖声、字幕挡脸、缺字、rights expired 和硬件编码失败。
7. Preflight/QC 必须阻断问题并路由到正确修正模块。
8. 中断 Final Render，验证 staging、segment cache、幂等和恢复。
9. 生成新 Final Candidate，执行全量 QC、demo/人工完整观看。
10. 形成 Release Review Package；只有人工 Gate 3 可 Release。

不得出现：旧 Alignment 配新字幕、FFmpeg 内暗调时长、无授权资产、QC unavailable 假 Pass、partial 文件注册、自动发布。

---

## 5. 质量与 Demo 验收

技术正确性按 Platform Profile；Craft Quality 按 Quality Standard 和 demo benchmark，分别报告 Voice、Audio、Subtitle、Visual/Sync 和整体观看体验。

通过必须同时满足：

- 所有 blocker 为零；
- 机器同步/响度/字幕/编码/rights 指标达标；
- 人工完整观看确认声音表演、BGM/SFX、字幕和画面不破坏 Stage 4 创意；
- 与 demo 的差距有时间码、原因和处理结果。

机器 QC 通过不能代替人工 Release Review。

---

## 6. 性能与容量

报告 TTS/Alignment/Mix/Subtitle/Render/QC 的 P50/P95、吞吐、峰值 CPU/RAM/Metal/disk、encoder session、token/cloud cost、cache hit 和每分钟成片成本。

多 Variant 并发必须验证 artifact 隔离、Project fairness、磁盘/热水位和交互 Preview 对 Final 的影响。具体并发数由每个 Resource Profile 实测固定。

---

## 7. 回滚与兼容

- Provider/Voice/Profile/Pronunciation/Font/Asset/Mix/Render compiler 回切创建新 Run。
- Voice/Alignment/Timeline/Subtitle/Mix/Render 通过新版本回退，历史不覆盖。
- Rights 撤销不能通过回滚旧 Manifest 绕过；必须替换资产或重新授权。
- FFmpeg/libass/font 变化运行 golden media/frame/audio 回归。
- Stage 6 QC/automation 接入不得改变 Stage 5 blocker 和 Gate 3 语义。

---

## 8. 完成定义

- 所有 Milestone、验收矩阵、故障注入和回滚演练通过。
- 至少一个真实项目完整生成 Voice、Mix、Subtitle、Final Candidate 和 Release Package。
- demo/项目人工评分达到版本化门槛且 blocker 为零。
- 所有媒体和字体/音色权利可审计。
- Gate 3 可独立复核并决定 Release/Revise/Reject。

---

## 9. 不得以此替代完成

- TTS 能出声不代表声音合格。
- 响度达标不代表人声可懂。
- ASS 能渲染不代表字幕可读或不挡人。
- FFmpeg exit 0 不代表成片正确。
- 技术 QC 通过不代表成片达到 demo 质量。
- 有 Release Package 不代表系统有权自动发布。

