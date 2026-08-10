# Coordination, Reflow and Preview

Version: 1.0

## 1. 目标

解决 Visual、Rhythm、Narration 和 Packaging 之间的相互约束，用有限、可追踪的协调循环产生可观看 Preview，而不是让模块循环修改直至偶然收敛。

输入：Planner PatchProposalSet、base TimelineRef、locks、Resource/Candidate Budget、Preview Profile。

输出：CoordinationPlan、ConflictResolution、ReflowReport、MasterTimelineDraft、PreviewPlan、PreviewArtifactRef。

---

## 2. 典型跨模块约束

- 镜头太短承载不了对白/解说和视觉信息。
- 解说太长挤压动作、反应和呼吸点。
- Hook 画面强但后续 Context Bridge 不成立。
- Crop 为保护主体保留了原片字幕区域，与新增包装冲突。
- 人工锁定镜头使目标总时长无解。
- 替换镜头改变 source audio/dialogue availability。

每个 Constraint 指明 owner、hardness、affected interval、inputs 和可选修复动作。

---

## 3. 协调循环

1. Compiler 合并最新 Proposal 并生成 ConflictSet。
2. 按最小影响范围分组。
3. 确定可调整维度和人工 locks。
4. Planner 只对授权 scope 提交 revision proposal。
5. Compiler 重验并计算 quality/cost delta。
6. 达到约束、无改进或 revision budget 后停止。
7. 剩余 hard conflict 转人工；soft conflict 保留风险。

循环上限、停止条件和选择规则配置化。禁止 Agent 无限互相“协商”。

---

## 4. Reflow 层级

- L0 item：单镜 trim/crop/text 微调。
- L1 beat：当前 Beat 内镜头/解说重新分配。
- L2 neighborhood：相邻 Beat 与 transition/context bridge。
- L3 sequence：整段 Narrative Spine。
- L4 variant：目标时长或 Strategy 需要改变，必须回 Gate 2/新 Brief。

默认从最小层级开始；扩大 scope 前输出 impact preview。Story/Strategy 不在 Stage 4 被隐式改写。

---

## 5. Preview 语义

Preview 使用同一 Master Timeline、transform、font/layout intent 和 compiler adapter，只降低分辨率、码率、特效质量或使用 placeholder audio。每个降级项写入 PreviewManifest。

Preview 必须明确：

- narration 是估时占位、临时 TTS 还是人工 scratch audio；
- subtitle/graphics 是 layout proxy 还是最终样式；
- crop/transition 是否与 final compiler 同语义；
- 哪些 Stage 5 资产尚未生成。

禁止使用独立前端逻辑制造与最终渲染不同的构图和时序假象。

---

## 6. 并发与缓存

不同 Conflict group 可并行求解，但重叠 interval 串行合并。不同 Variant preview 并行，受 render admission 控制。共享 clip conform/crop cache 以 Timeline segment checksum 标识。

Preview Activity 幂等；失败不改变 Timeline 状态。局部 Preview 只渲染修改区间及上下文 handles，正式全片审核仍需完整 Preview。

---

## 7. 人工优先与冲突

人工 lock 永远高于 AI soft preference。若人工 lock 与事实、rights、平台或非法时间 hard constraint 冲突，系统必须明确阻止并说明，不可盲从。

AI 建议必须展示修改前后 Timeline diff、影响范围、理由和预计时长变化。接受/拒绝建议都进入 Correction 数据。

---

## 8. 测试与验收

- 构造跨模块无解、循环修改和 revision budget 耗尽场景。
- Reflow 不越过 scope lock，扩大范围需要显式批准。
- Preview/Final adapter 对时间和 crop 几何保持一致。
- placeholder 状态不会被误标为 Stage 5 正式资产。
- 局部 preview cache 在 dependency 变化后正确失效。
- 人工接受/拒绝 AI Proposal 均可追踪并可撤销。

