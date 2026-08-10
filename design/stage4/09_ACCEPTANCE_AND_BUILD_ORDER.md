# Stage 4 Acceptance and Build Order

Version: 1.0

## 1. 目标与契约

目标：规定 Creative Timeline Engineering 的依赖顺序、可独立退出条件、demo 对比、容量测试、回滚和 Stage 5 交接标准。

输入：Stage 1–3 已批准能力、Stage 4 设计、demo asset、Evaluation Dataset、Quality/Resource/Profile 配置和测试环境。

输出：Milestone Evidence、Stage4 Acceptance Report、Demo Comparison、Capacity Baseline、Risk Register、Rollback Record、Stage5 Handoff Approval。

---

## 2. 构建顺序

### Milestone 1 — Creative Timeline Contracts

- NarrativeBeat、PatchProposal、Conflict、CropPath、Rhythm、Narration schemas
- Timeline ownership/placeholder/lock/intent semantics
- Compiler validator、dependency rules、OTIO adapter updates

退出：Schema、invariants、Patch/CAS、round-trip 和失效测试通过。

### Milestone 2 — Clip Retrieval and Continuity

- multi-route retrieval、candidate features、coverage
- sequence selection、continuity graph、pin/ban/replace

退出：关键 Beat coverage、错人物/时间阻断、序列 benchmark 和局部重算通过。

### Milestone 3 — Visual Reframe

- composition targets、CropPath solver、stability
- source subtitle handling、fallback、manual keyframe

退出：主体覆盖、稳定性、safe area、复杂多人/字幕降级和 preview parity 通过。

### Milestone 4 — Rhythm Engineering

- BeatBudget、RhythmCurve、ShotDuration/Transition
- DurationConflict、breathing/payoff、local reflow

退出：总时长对账、结构规则、人工完整观看和 scope lock 通过。

### Milestone 5 — Narration Engineering

- outline/draft/global passes
- evidence/redundancy/fact/coreference/duration checks
- pronunciation、manual edit/lock/local regeneration

退出：关键句证据、事实 blocker、口语/画面价值和估时 baseline 通过。

### Milestone 6 — Coordination and Preview

- bounded coordination loop、Conflict resolution、scope escalation
- PreviewPlan/compiler/cache、partial/full preview

退出：无无限循环、无跨 scope 覆盖、Preview/Final 语义一致、失败恢复通过。

### Milestone 7 — Workspace and Demo Benchmark

- professional Timeline Review interactions
- demo reverse-engineered artifact/rubric
- version diff、Correction、Approve Timeline Intent

退出：人工可精确修正并完成基于时间码的 demo 对比审核。

### Milestone 8 — Production Qualification

- quality/capacity benchmark、failure injection
- dashboards/runbooks、feedback candidate、rollback rehearsal

退出：固定输入与 Resource Profile 的质量、成本、恢复和审核效率报告获批准。

---

## 3. 验收矩阵

| 维度 | 必须证明 |
|---|---|
| Timeline | 单一 timebase、合法区间、Patch/CAS、无静默漂移 |
| Evidence | Clip 与关键 Narration 可追溯到 Story/source |
| Visual | 选材、连续性、主体构图、CropPath、fallback |
| Rhythm | Beat budget、张弛、Hook bridge、breathing、payoff |
| Narration | 事实、口语、非复述、全篇一致、时长估算 |
| Coordination | typed Proposal、有限循环、Conflict、scope lock |
| Preview | 与 final compiler 同语义、placeholder 明确、可恢复 |
| Review | 精确编辑、diff、undo/redo、stale 防护、Approval |
| Demo | 版本化结构/人工 benchmark 与差距时间码 |
| Incremental | 局部 reflow/regen 和 dependency closure 正确 |
| Operations | 并发、资源、成本、trace、runbook、rollback |

---

## 4. 端到端验收场景

1. 读取冻结的 ApprovedCreativeBriefRef 与多集 Story/Media。
2. 生成 Beat Graph，并行 Visual/Rhythm/Narration Proposals。
3. 注入错人物镜头、无解时长、多人竖裁和虚构心理解说。
4. Compiler 必须阻断错误并输出最小 ConflictSet。
5. 生成含 fallback、Narration placeholder 和风险标记的 Timeline Draft。
6. 中断 Planner/Preview Worker，验证恢复与幂等。
7. 人工锁定镜头、调整 crop、停顿和一句解说，执行局部 reflow。
8. 验证范围外 Timeline 不漂移，Stage 5 依赖正确失效。
9. 完整观看 Preview，与 demo benchmark 逐维度记录问题时间码。
10. 批准 Timeline Intent，冻结 Brief/Story/Profile/Compiler/benchmark versions。

不得出现：Planner 直接覆盖 Timeline、无关镜头填空、自动裁掉关键主体、解说编造、无限 reflow、Preview 与 Final 语义分叉。

---

## 5. Demo 与质量验收

Demo 对比至少报告：Hook/Context/Payoff 结构、镜头时长分布、信息密度、原声/留白、构图、解说功能/语体和包装意图。

通过条件使用版本化 Quality Profile：

- correctness blocker 为零；
- 机器可测 Timeline/构图/证据指标达标；
- AI Drama Producer 与 Review Director 的完整观看审核达到要求；
- 差异具有明确创作理由，不能用平均数接近 demo 代替观看质量。

Stage 4 只评价可预览的创意时间线；正式 TTS、音频、字幕和渲染质量在 Stage 5 签收。

---

## 6. 性能与容量

报告长剧/多 Variant 下的 retrieval、solver、crop、model、preview P50/P95，峰值 CPU/RAM/Metal/disk、缓存命中、每分钟 Timeline 规划成本和人工审核时间。

Candidate/Revision/Preview Budget 必须在执行前限制组合增长。个人 Mac mini 建立首个 profile，并记录热限制和交互 preview 对后台任务的影响。

---

## 7. 回滚与兼容

- Timeline/Patch/Correction 通过后继版本回退，历史不覆盖。
- Compiler/Solver/Profile/Prompt 回切创建新 Run 并可重放 benchmark。
- 人工 locks、approved decisions 和 accepted risks 在迁移中保持。
- OTIO adapter 破坏性变化提供 LossReport 和兼容迁移。
- Stage 5 Contract 变更不反向改变已批准 Timeline Intent；通过 adapter/version negotiation 处理。

---

## 8. 完成定义

- 所有 Milestone、验收矩阵和故障演练通过。
- demo benchmark artifact 和人工 rubric 完成并版本化。
- 至少一个真实项目从 Brief 生成可精修 Preview 并完成 Correction/Approval。
- Stage 5 只依赖 ApprovedTimelineIntentRef 和公共 Artifact/Media Contract。
- 人工可精确修改镜头、构图、Beat、停顿和解说且局部重算可靠。

---

## 9. 不得以此替代完成

- Timeline JSON 合法不代表成片可看。
- 平均镜头短不代表节奏好。
- 自动追脸不代表竖屏构图正确。
- 解说没有事实错误不代表有画面价值。
- 局部 Preview 顺畅不代表完整叙事成立。
- 与 demo 数值相似不代表达到 demo 的创作质量。

