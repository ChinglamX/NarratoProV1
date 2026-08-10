# Production Implementation Blueprint

Version: 1.0

## 1. 目标

把六阶段架构转换为可直接编码的模块化单体实施蓝图，统一 Repository、Package、API、Schema、Workflow、Epic 和首批任务，避免各阶段独立实现后产生第二套状态、时间线或数据契约。

---

## 2. 输入

- 项目纲领、架构、工程与质量规则
- `design/architecture/` 总体设计
- `design/stage1/` 到 `design/stage6/` 详细规格
- Temporal、PostgreSQL、Object Store、Master Timeline、Provider Interface 等技术决策

---

## 3. 输出文件

- `01_ARCHITECTURE_REVIEW.md`：全局审计结论与问题收敛
- `02_REPOSITORY_LAYOUT.md`：目录、部署单元与所有权
- `03_PACKAGE_DEPENDENCY_RULES.md`：包依赖和模块边界
- `04_API_AND_COMMAND_MODEL.md`：外部 API、Command、Query、Event
- `05_SCHEMA_AND_ARTIFACT_CATALOG.md`：跨阶段唯一 Schema/Artifact 目录
- `06_WORKFLOW_AND_DEPLOYMENT_MAP.md`：Temporal、Task Queue、Worker 和环境
- `07_EPICS_AND_DELIVERY_SEQUENCE.md`：生产 Epic 与依赖顺序
- `08_INITIAL_IMPLEMENTATION_BACKLOG.md`：首批可编码任务与验收
- `09_ARCHITECTURE_DECISIONS.md`：必须冻结的 ADR 决策
- `10_CONTEXT_AND_RECOVERY.md`：项目记忆、上下文重建与恢复

校准计划不在本目录重复定义，统一引用 `design/calibration/README.md`。

---

## 4. 实施原则

- 首个生产形态是模块化单体，不是微服务集合。
- 一个概念只能有一个所有者、一个 canonical Schema 和一个真相源。
- API 负责命令/查询，不执行长任务。
- Temporal 负责耐久执行，不替代业务数据库。
- Artifact 不可变；Correction、Approval 和回滚均产生新版本或 pointer event。
- Stage 是交付依赖，不直接等于代码目录或微服务。
- Provider、Profile、Prompt 和 Policy 通过注册表/接口接入。
- Web UI 不复制核心业务规则；所有提交都走公共 API。
- 实现顺序从 Contract/Invariant 开始，不从模型或页面开始。

---

## 5. 完成标准

- 六阶段所有正式输入输出都能在 Schema Catalog 找到唯一名称和所有者。
- Package Dependency Graph 无循环依赖。
- 每个 Workflow Activity 映射到一个 Application Use Case 和 Resource Queue。
- 三个正式 Gate 与内部 Review Checkpoint 边界明确。
- 首批任务每项具有输入、输出、测试和退出条件。
- 后续实现不需要重新决定数据库真相源、Timeline 所有权或 Provider 边界。
