# Agent Context Loading

项目上下文不以会话为真相源。每次任务启动、上下文压缩、中断恢复或 Agent 交接时：

Step 1：读取 `README.md` 和 `AGENTS.md`。

Step 2：读取 `PROJECT_INDEX.md` 和 `PROJECT_STATE.md`，识别当前 Lifecycle、Release、Epic、Task 和恢复点。

Step 3：执行 `agent/CONTEXT_RECONSTRUCTION_PROTOCOL.md`，校验实际 workspace/Git/runtime。

Step 4：识别任务类型并加载对应 Role、质量规则和 `PROJECT_INDEX.md` 指定的任务文件。

Step 5：确认 Completed、Not Implemented、Risk、Open Decision、Expected Output 和 Validation。

Step 6：执行任务。重要任务完成后更新 `PROJECT_STATE.md`；跨会话或未完成任务使用 `agent/HANDOFF_TEMPLATE.md`。

禁止只依赖压缩摘要直接继续，也禁止因 State 落后而重复覆盖已存在文件；先对账和修正状态。



---

# Task Report Format

重要任务统一使用 AGENTS.md 第 5 节定义的格式：

- Task Type
- Active Role
- Objective
- Input
- Implementation / Decision
- Output
- Quality Check
- Risk
- Next Step
- Project State Impact
- Handoff（适用时）

本文件不另行定义第二套报告格式。
