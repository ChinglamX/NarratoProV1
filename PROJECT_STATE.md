# Project Current State

State Version: 9
Last Updated: 2026-08-11
State Owner: Project

## 1. 当前阶段

- Lifecycle：Implementation started; E00 bootstrap in runtime acceptance.
- Active Release Slice：R1 Foundation。
- Active Epics：E00 Engineering Bootstrap。
- Active Backlog Entry：A03 Local Infrastructure runtime acceptance。
- Automation：L1；Confidence 仅 Shadow。未授权任何 L2/L3 自动放行。

---

## 2. 已完成且已审计

- 项目纲领、能力、五域架构、工程与质量规范。
- Stage 1–6 的生产级详细设计。
- 全局 Architecture Review 与模块化单体实施蓝图。
- Repository、Package、API、Schema Catalog、Workflow、Epic 和首批 Backlog 设计。
- Calibration Program、Calibration Pack v1 和持续运营规范。
- 上下文重建、项目索引和阶段恢复机制设计。
- 强制启动协议已接入 `AGENTS.md`、Roadmap、E00 Epic 和 A06 Backlog。
- A01 Repository Scaffold：Python 3.11 workspace、API/Worker/CLI、React Review Web、统一 Make/pnpm 入口已实现并通过安装/构建检查。
- A02 Quality Toolchain：format/lint/mypy/pytest/Bandit、依赖边界错误 fixture 和 GitHub CI 已实现。
- A04 Configuration Bootstrap：typed settings、secret-safe summary、PostgreSQL/fail-fast production 校验已实现。
- A05 Calibration Manifest Bootstrap：Pack/Dataset/Split/Slice/Guideline/Rights contracts 和空 Pack v1 registry 已实现；split leakage 与 Frozen Test 防误用测试通过。
- A06 Context Integrity Bootstrap：required files、Index links、State↔Epic/Backlog、Handoff、Cold-start Drill 已进入本地和 CI 检查。

设计完成不等于代码完成；不得把上述项目报告为已实现能力。

---

## 3. 尚未开始

- A03 PostgreSQL/Temporal/Object Store/OTel/Prometheus/Grafana 已有固定版本 Compose 配置和可恢复的串行镜像拉取，但尚未完成全部镜像拉取、真实启动、health/restart/persistence 验收。
- B01 起 Canonical Contracts 和数据库 migrations 实现。
- Master Timeline、Provider、Review Workspace 和媒体 Pipeline 代码。
- Calibration Pack 的真实素材标注和 Baseline。
- 任何 L2/L3 自动化。

---

## 4. 下一步唯一恢复点

按 `design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md` 开始：

1. 完成 A03 Local Infrastructure runtime acceptance：真实启动、health/readiness、restart 和 volume persistence。
2. 保存 A01–A06 实施 checkpoint 与 Handoff。
3. 开始 B01 Foundation Value Objects，随后 B02–B05。

开始编码前必须验证工作区状态、选择包管理/版本并将决定写入 ADR/State。

---

## 5. 当前阻断与风险

- 初始设计基线 tag `architecture-baseline-v1.0.0` 指向 `de4e31c`；A01–A06 当前 checkpoint 以本 State 所在 Git revision 为准。
- Python resolution lock 尚未建立；Web 已生成 `pnpm-lock.yaml`。
- A03 只通过 Compose 静态解析，真实基础设施验收仍未执行。
- Docker Desktop 已启动；PostgreSQL、Temporal、Temporal UI、MinIO、OTel 固定镜像已缓存，Prometheus blob 下载持续 EOF，Grafana 尚未开始。未创建项目容器或 volume。网络恢复后重试 A03，不更换未验证镜像规避失败。
- 后续诊断确认宿主可访问 Registry，Docker daemon 使用 `http.docker.internal:3128` 代理并在 CloudFront blob 下载时 EOF；不得静默修改全局 Docker 代理。
- 2026-08-11 经用户授权临时将 Docker Desktop `vm.proxy.mode` 从 `system` 切换为 `disabled`：daemon 直连 `registry-1.docker.io` 持续 `context deadline exceeded`，证明当前环境不能依靠直连绕过代理。实验后已恢复 `system`，settings-store 与实验前备份逐字一致。
- 经用户授权临时关闭 containerd image store：Temporal 镜像下载成功，但 Compose 并行拉取随后使 daemon 无响应；已恢复原设置并重启 Docker。不得重复该路径或把部分镜像下载当作 A03 验收。
- 真实 Provider、模型权重、字体、音乐和音色的生产许可尚未完成准入。
- Calibration Pack 尚无真实项目 Gold/Baseline。
- demo 已存在于项目，但完整人工 benchmark artifact 尚未建设。

---

## 6. 未决决策

- Python resolution lock 工具选择（要求不改变 PEP 621 package source）。
- A03 同时提供本地文件系统路径和 MinIO；E02 必须决定首个正式 Object Store adapter 的默认实现。
- FFmpeg 首个生产锁定版本仍需在 E04/E05 media acceptance 中确定。

未决决策必须通过证据、兼容性和 ADR 解决，不能由 Agent 默认偏好静默决定。

---

## 7. 最近验证

- 六阶段、实施和校准设计入口全部存在。
- Markdown `git diff --check` 通过。
- 未发现旧 `Product V0.1`、`Python DAG` 或已废弃角色术语。
- 详细设计与实施/校准文档约 8,000+ 行；数量不是完成依据，权威入口以 `PROJECT_INDEX.md` 为准。
- Cold-start 检查：Index/State/Protocol/Handoff/Backlog 引用存在，active E00/A03 和当前风险可恢复。
- Git 根提交 `7f7591c` 已保存全部设计/治理文件；本地 demo 视频与抽帧由 `.gitignore` 排除。
- `make check`：17 tests、92.31% coverage、Ruff、strict mypy、Bandit、Context/Architecture checks 通过。
- Review Web：TypeScript typecheck 与 Vite production build 通过，依赖由 `pnpm-lock.yaml` 锁定。
- Compose：固定镜像配置通过 `docker compose ... config --quiet`；未启动服务。
- A03 runtime 尝试：Docker daemon 29.5.3 可用；镜像授权/manifest 请求 EOF，`compose ps -a` 和项目 volume 检查为空。
- A03 acceptance 已固化为 `make infra-accept`：覆盖启动等待、PostgreSQL/MinIO persistence probe、全服务 restart、再次 health 和最终状态；单元测试验证步骤完整。
- 2026-08-11 A03 runtime：containerd image store 关闭实验只解决 Temporal 单镜像下载，未完成全栈启动；实验已回滚，Docker 29.5.3/原设置恢复，项目 container/volume 为空。
- 2026-08-11 A03 recovery：验收脚本改为从 Compose 动态读取镜像、去重后串行拉取、每镜像最多 5 次指数退避，并以 `--pull never` 启动；PostgreSQL probe 改用容器有效配置。定向测试 4 项通过。
- 串行恢复已缓存 `postgres:16.4`、`temporalio/auto-setup:1.25.2`、`temporalio/ui:2.31.2`、`minio/minio:RELEASE.2024-11-07T00-52-20Z`、`otel/opentelemetry-collector-contrib:0.113.0`；`prom/prometheus:v2.55.1` 连续两轮有界重试仍在 Docker Hub/CloudFront blob 请求 EOF，故未进入服务启动。Docker 29.5.3 正常，项目 container/volume 为空。
- 代理隔离实验：Docker Desktop API 确认原模式为 `system`，macOS 系统代理为 `127.0.0.1:7890`；临时 `disabled` 后 registry manifest HEAD 超时，未改善拉取。已中止重试、恢复原设置并重启 Docker；最终 API=`system`、settings-store backup cmp=0、daemon 正常、项目 container/volume 为空。A03 仍未通过。

---

## 8. 恢复确认

新 Agent 应能在不读取历史会话的情况下回答：

- 项目目标是什么？
- 当前做到哪里？
- 哪些只是设计、哪些已实现？
- 下一项任务是什么？
- 哪些核心决策不可重做？
- 哪些风险/未决选择需要处理？

无法回答时，Context Reconstruction 未完成，不得开始修改。
