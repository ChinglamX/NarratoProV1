# Context Reconstruction Protocol

Version: 1.0

## 1. 目标

确保新会话、上下文压缩、Agent 更换、长任务中断或阶段回溯后，可以只依靠项目文件恢复正确目标、状态、约束和下一步。

聊天历史、Agent summary 和模型记忆只能作为线索，不能作为项目真相源。

---

## 2. 触发条件

以下任一情况必须执行完整或增量恢复：

- 新会话或新 Agent 首次进入项目。
- 上下文被压缩或摘要替换。
- 距上次任务较久，无法确认当前状态。
- 接手他人或其他 Agent 未完成任务。
- Workflow/终端/编辑中断后恢复。
- 用户要求“继续”，但当前具体恢复点不在有效上下文中。
- 发现聊天结论与项目文件不一致。

---

## 3. 冷启动恢复

### Step 1 — 定位项目

确认工作区根目录，读取 `README.md` 和 `AGENTS.md`。不得根据目录名猜项目目的。

### Step 2 — 读取导航与状态

完整读取 `PROJECT_INDEX.md`、`PROJECT_STATE.md` 和本协议。

### Step 3 — 校验实际工作区

只读检查：

- 文件/目录是否存在；
- Git branch/status/log（如已建立）；
- active task 对应文件是否存在；
- 当前变更是否与 State 相符；
- 有无运行中的任务、失败输出或未提交迁移。

Git、终端和运行状态是证据，但不能自动覆盖 State；发现差异要登记并判断哪一侧过期。

### Step 4 — 按任务加载

使用 `PROJECT_INDEX.md` 第 7 节加载当前 TYPE/Role、工程/质量和相关 Stage/Epic 文件。禁止无目的读取全部 8,000 行，也禁止只读 State 就编码。

### Step 5 — 输出 Reconstruction Check

在内部工作记录或 commentary 中明确：

- Project Identity/Goal
- Current Lifecycle/Release/Epic/Task
- Completed vs Not Implemented
- Canonical contracts/ADRs relevant to task
- Workspace/Git/Runtime state
- Risks/Blockers/Open decisions
- Intended action and verification

### Step 6 — 开始任务

只有 State、实际文件和用户请求一致时开始。若不一致会影响方向，先修复 State/Index 或请求用户决定。

---

## 4. 上下文压缩后的增量恢复

压缩后不要从头重做已经完成的工作：

1. 重新读取 `PROJECT_STATE.md`。
2. 读取当前 task 的 Handoff/plan/output files。
3. 检查实际 diff、tests、running process。
4. 将摘要中的结论与 State/Artifact 对账。
5. 从最近一个有验证证据的 checkpoint 继续。

如果摘要说“完成”而 State/测试没有证据，按未验证处理。若文件已经完成而 State 未更新，先审计并补状态，不重复实现。

---

## 5. 中断任务恢复

按照以下优先级找 checkpoint：

1. 已提交且测试通过的 Git commit/tag（建立后）。
2. `PROJECT_STATE.md` 的最近验证与 active task。
3. 任务 Handoff Record。
4. 实际文件 diff 和测试输出。
5. Temporal/Artifact/Audit 状态（系统实现后）。
6. 聊天摘要，仅用于补充。

恢复前识别：最后成功步骤、部分写入、未运行测试、正在运行的进程、外部副作用和需要回滚/继续的精确目标。

禁止看到半成品后从头覆盖，也禁止把未验证文件标完成。

---

## 6. 阶段回溯

当后续阶段发现上游设计或实现错误：

1. 创建 Issue/Decision，说明发现阶段和根因阶段。
2. 定位 Canonical Contract/ADR/Artifact owner。
3. 计算影响：Schema、Workflow、Artifact、Calibration、downstream stages。
4. 决定 correction、migration 或 ADR change。
5. 更新上游设计/实现及所有依赖测试。
6. 将下游状态标 stale/revalidation required，而不是假定仍有效。
7. 更新 `PROJECT_STATE.md` 的 active recovery point。

回溯不删除历史完成记录；记录 superseded 和新的验证证据。

---

## 7. 任务结束交接

重要任务结束必须：

- 更新 `PROJECT_STATE.md`：完成、进行中、下一步、风险、验证。
- 若改变方向/契约，更新 `PROJECT_INDEX.md`、Catalog/ADR/Roadmap。
- 使用 `agent/HANDOFF_TEMPLATE.md` 形成简明交接记录；可写入 State 或任务 artifact。
- 记录真实测试命令/结果，不能只写“已验证”。
- 明确未完成项和禁止下一 Agent 假定的事项。

无需为纯解释且未改变项目状态的对话更新 State。

---

## 8. 状态写入规则

- State 是当前事实摘要，不是计划愿望清单。
- 只有验证完成才进入 Completed。
- 设计完成和代码完成必须分开。
- 用户尚未授权的外部发布、Git commit 或 destructive action 不得写成待自动执行。
- 状态更新使用短结论和链接，不复制详细文档。
- 同时只能有一个主 Active Task；并行任务列为 bounded tracks。

---

## 9. 恢复测试

定期执行 Cold-start Drill：给一个没有聊天历史的 Agent，只提供工作区，要求在有限时间内输出 Reconstruction Check。

通过条件：

- 正确识别项目目标和当前阶段。
- 区分设计完成与代码未开始。
- 找到下一任务 A01 及其依赖。
- 识别三个正式 Gate、唯一 Timeline 和 L1/Shadow。
- 识别 Git 基线风险和未决工具链。
- 不重复 Stage 1–6 设计，不直接接入模型或启动错误 Epic。

