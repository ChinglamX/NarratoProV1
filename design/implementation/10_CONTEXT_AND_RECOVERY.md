# Context, Project Memory and Recovery

Version: 1.0

## 1. 目标

把 Agent 上下文重建、项目状态、任务交接和阶段回溯实现为项目治理能力，确保项目方向不依赖任何单一会话或模型记忆。

输入：Canonical Index、Project State、Git/Workspace evidence、Backlog、Run/Artifact/Audit state。

输出：ReconstructedContext、StateUpdate、HandoffRecord、RecoveryPlan、StaleImpactSet。

---

## 2. 三层项目记忆

### Stable Memory

Charter、Rules、Architecture、Quality、Workflow、ADR、Schema Catalog。变化低、优先级高。

### Operational Memory

`PROJECT_STATE.md`：当前 Epic/Task、完成/未实现、风险、未决决策和最近验证。

### Execution Memory

Git commits/diffs、CI/tests、Temporal history、Artifact lineage、Audit、Handoff。用于证明某一步实际发生。

聊天只属于临时 Working Memory，不进入权威层。

---

## 3. State Schema（未来机器可读）

后续可从 Markdown 旁生成/维护 `project_state.yaml`：

```yaml
state_version: integer
updated_at: datetime
lifecycle: architecture | implementation | production
active_release: string
active_epic: string
active_task: string
completed_capabilities: [object]
not_implemented: [string]
blocked_by: [object]
open_decisions: [object]
last_validations: [object]
workspace_snapshot: object
next_step: object
canonical_refs: [string]
```

Markdown 是当前人类可读入口；机器可读格式必须由同一 Schema 生成或同步校验，禁止双真相源。

---

## 4. Context Manifest

每个 Backlog Task 最终应声明：

- task_id/type/role；
- required canonical refs；
- optional domain refs；
- inputs/expected outputs；
- invariants/ADRs；
- validation commands；
- state transition；
- rollback/handoff requirements。

Agent Host 根据 Manifest 按需加载，避免全量上下文和遗漏关键约束。

---

## 5. Recovery Checkpoint

工程任务 checkpoint 至少包含 git revision/diff、state version、active task、tests、migrations、running workflow/process 和 external effects。

生产任务 checkpoint 使用 Project/Run/StageExecution、ArtifactRefs、Review state、Temporal workflow/build ID、effective configs 和 cost/resource state。

Checkpoint 只有验证成功后才能成为 resume point；partial 状态明确标注。

---

## 6. 回溯与失效

设计/实现变更使用与 Artifact 相同的影响思想：

- ADR/Contract 变化 → 标记相关 Epics/tests/calibration stale。
- Provider/Prompt/Config 变化 → 相关 benchmark/calibration stale。
- State 与实际 workspace 不符 → 停止新任务，先 reconcile。
- 回滚选择已验证 checkpoint，保留后继历史。

未来实现 `ContextIntegrityCheck` 和 `StateReconciler`，但不得自动猜测核心决策。

---

## 7. CI 与自动检查

首批加入：

- required context files 存在。
- Index 链接解析。
- State active Epic/Task 与 Catalog/Backlog 一致。
- State version 单调递增。
- 设计完成/代码完成使用不同状态。
- Handoff schema lint。
- 核心目录/Contract/ADR 变更要求 state impact declaration。

后续加入：Schema Catalog 与代码扫描、Git/State revision 对账、Artifact/Temporal recovery drill。

---

## 8. 安全边界

恢复协议不授权额外操作。发现未提交变更、运行进程、外部发布或 destructive migration 时必须按原授权范围处理。

State/Index 不能保存 secret、签名 URL、个人敏感数据或大模型原始上下文。

Agent 不能以“恢复项目”为理由覆盖用户变更或自动提交/发布。

---

## 9. 测试与验收

- New Session Drill：无聊天历史正确找到 active task。
- Compaction Drill：摘要错误时以 State/文件为准并发现冲突。
- Interrupted Edit Drill：识别 partial diff 和未运行测试，不重复覆盖。
- Stage Backtrack Drill：Contract 变化产生 StaleImpactSet 和新 recovery point。
- State Drift Drill：State/Backlog/Git 不一致时 fail closed。
- Different Agent Drill：另一代码 Agent 能输出相同核心目标、边界和下一步。

