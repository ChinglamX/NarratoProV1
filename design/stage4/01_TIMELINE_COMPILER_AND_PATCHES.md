# Timeline Compiler and Patch Proposals

Version: 1.0

## 1. 目标

将 Narrative Beat、Visual、Rhythm、Narration 和 Packaging Proposal 确定性合并为合法 Master Timeline，并把无法兼容的要求输出为结构化 Conflict，而不是隐式覆盖。

输入：ApprovedCreativeBriefRef、base TimelineRef、PatchProposalSet、Platform/Duration Profile。

输出：MasterTimelineDraft、ConstraintReport、ConflictSet、MergeReport、DependencyDelta。

---

## 2. 核心工具与边界

- 项目内部强类型 Timeline Schema：业务真相源。
- Pydantic/JSON Schema：契约与运行时校验。
- OpenTimelineIO：编辑交换和 round-trip adapter，不承担项目全部私有语义。
- PostgreSQL/Artifact Registry：版本、CAS、lineage 与依赖。
- FFmpeg plan adapter：只在 preview/Stage 5 编译，不反向成为 Timeline 真相源。

禁止 Planner 直接输出 FFmpeg command 作为正式创意结果。

---

## 3. Timeline 层次

```text
Sequence
  ├─ Narrative Beats / Markers
  ├─ video_main / video_overlay
  ├─ original_audio intent
  ├─ narration placeholder
  ├─ subtitle/overlay intent
  └─ transitions/effects intent
```

Timeline Item 同时记录 source range、timeline range、transform、evidence/story/strategy refs、generation dependencies 和 ownership metadata。

Stage 4 的 narration/subtitle/audio 条目允许 placeholder/intent 状态；Stage 5 用正式 Voice/Alignment/Mix/Subtitle artifacts 替换，而不改变引用语义。

---

## 4. Patch Proposal

Proposal 包含：proposal_id、planner、base_timeline_version、scope、operations、constraints、priority class、rationale、dependencies、expected impact。

Operation 使用语义动作：insert/remove/move/trim/split/replace/retime/set_transform/set_text/set_intent/set_marker。每项声明 expected item version 和允许修改范围。

Proposal 状态：proposed、validated、conflicted、accepted、rejected、superseded。验证失败不能通过修改原 Proposal“补成功”，必须创建后继版本。

---

## 5. 约束分类

Hard：总时长上限、合法 source range、无负时长、证据/Story 正确性、rights、platform、人工锁定、track invariant、Hook continuation。

Negotiable：beat duration、镜头候选、解说措辞、转场和呼吸点。

Soft：类型节奏偏好、视觉变化、平均镜头长度、文风和包装密度。

优先级固定：hard safety/fact → human lock → approved brief intent → cross-track sync → negotiable → soft preference。

---

## 6. 合并算法

1. 校验所有 Proposal 的 base version 和 scope。
2. 标准化为 canonical operations 并建立读写集合。
3. 检测 item/interval/semantic dependency 冲突。
4. 先应用无冲突 hard operations。
5. 对 negotiable constraint 执行有限优化/搜索。
6. 对无法求解项生成 ConflictSet 和最小冲突范围。
7. 运行 Timeline Validator、duration/continuity/evidence checks。
8. CAS 提交新 Timeline version 和 DependencyDelta。

不采用 last-write-wins。优化器目标函数和权重必须版本化，求解超时后返回 best-known + unresolved，不假装最优。

---

## 7. 并发与重放

Planner 可并行计算；单 Timeline commit 串行。不同 Variant 并行。相同 base 的 Proposal 可并行验证，合并使用 deterministic ordering 和固定 solver seed。

人工编辑产生最高优先级且带 scope lock 的 Patch。AI 重新规划时必须读取最新 base；stale Proposal 需要自动 rebase 成功或进入 Conflict，禁止覆盖人工修改。

---

## 8. 失效与回滚

- Clip trim/replace：失效相关 continuity、crop、rhythm、narration fit、preview。
- Narration text/duration intent：失效 narration estimate、rhythm fit、Stage 5 voice/alignment/subtitle/mix/render。
- CropPath：失效视觉 preview/render，不失效 Story。
- Beat order：失效 downstream sequence-level continuity/rhythm/narration。

回滚选择先前 TimelineRef 创建新的 active version，不删除后继版本。OTIO 导入产生新 Proposal 并输出 LossReport，不直接覆盖 Master Timeline。

---

## 9. 测试与验收

- overlapping edits、stale base、人工 lock、非法 source range 和负时长。
- 相同输入/seed 产生相同 canonical Timeline。
- 无解 constraint 输出最小冲突，不无限求解。
- OTIO round-trip 保留关键 Clip/Track/Transition/Marker 和私有 metadata。
- Patch 应用/撤销保持 lineage 与精准依赖失效。
- Planner 失败不损坏 base Timeline。

