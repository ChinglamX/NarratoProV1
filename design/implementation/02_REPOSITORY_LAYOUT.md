# Repository Layout

Version: 1.0

## 1. 目标

定义首个生产实现的模块化单体目录、部署单元和代码所有权，使业务域可独立测试并在有证据时拆分，而不是提前微服务化。

输入：五域架构、六阶段设计、Python/TypeScript 技术栈。

输出：Repository Tree、Module Ownership、Deployment Units、Test Layout。

---

## 2. Canonical Layout

```text
NarratoProV1/
├── apps/
│   ├── api/                    # FastAPI composition root
│   ├── worker/                 # Temporal worker entrypoints
│   ├── review_web/             # TypeScript/React workspace
│   └── cli/                    # operator/developer CLI
├── packages/
│   ├── contracts/              # Pydantic/JSON Schema/OpenAPI shared contracts
│   ├── foundation/             # IDs, errors, clock, checksum, config primitives
│   ├── artifacts/              # Artifact registry, blob, dependency/invalidation
│   ├── control/                # project/run/policy/review/resource orchestration
│   ├── timeline/               # Master Timeline, patch, validator, OTIO/compiler
│   ├── intelligence/           # media, observation, identity, fact, story use cases
│   ├── strategy/               # profiles, selling points, strategy, hook, variants
│   ├── production/             # clip/crop/rhythm/narration/voice/audio/subtitle/render
│   ├── evaluation/             # QC, correction datasets, calibration, automation, online
│   ├── providers/              # provider protocols and adapters
│   ├── persistence/            # SQLAlchemy repositories, Unit of Work, migrations helpers
│   ├── observability/          # OTel/log/metric conventions
│   └── testing/                # fixtures, golden artifacts, provider fakes
├── workflows/
│   ├── project/
│   ├── intelligence/
│   ├── strategy/
│   ├── timeline/
│   ├── production/
│   └── evaluation/
├── migrations/                # Alembic revisions
├── configs/
│   ├── schemas/
│   ├── profiles/
│   ├── policies/
│   └── prompts/
├── benchmarks/
│   ├── manifests/
│   ├── guidelines/
│   └── expected/
├── tests/
│   ├── contract/
│   ├── unit/
│   ├── integration/
│   ├── workflow_replay/
│   ├── golden/
│   ├── load/
│   └── failure_injection/
├── deploy/
│   ├── compose/
│   ├── temporal/
│   ├── observability/
│   └── runbooks/
├── scripts/                    # thin operator scripts; no business logic
├── generated/contracts/        # immutable versioned JSON Schema/OpenAPI/Artifact registries
└── design/
```

---

## 3. Python Package 结构

每个 domain package 内部统一：

```text
domain/
├── domain/          # entities, value objects, invariants, domain services
├── application/     # commands, queries, use cases, ports
├── adapters/        # provider/persistence/media integrations
├── api/             # HTTP/worker DTO mapping; optional
└── tests/
```

Domain 不依赖 FastAPI、Temporal、SQLAlchemy 实现或具体模型 SDK。Composition root 在 `apps` 组装 ports/adapters。

---

## 4. 部署单元

首个生产部署仍来自同一仓库/版本：

- API process：命令、查询、Review 和签名媒体访问。
- CPU media worker：FFmpeg、OpenCV、probe、mix、QC。
- Audio ML worker：ASR、alignment、TTS。
- Vision ML worker：OCR、detection、embedding、VLM。
- Cloud model worker：受限外部 LLM/VLM/TTS。
- Render worker：preview/final，独立资源队列。
- Evaluation worker：benchmark、calibration、dataset、online analysis。
- Review Web：静态前端应用。

这些是可独立扩展进程，不是独立微服务数据库。它们共享版本化 Contract、PostgreSQL、Object Store 和 Temporal。

---

## 5. 配置与生成物

- `configs/` 保存可审阅源文件；批准后注册为 immutable Config Artifact。
- JSON Schema/OpenAPI 由 `packages/contracts` 生成；审计基线保存到 `generated/contracts/versions/<semver>`，TypeScript 类型生成到 Review Web。版本目录不可覆盖，禁止手工维护第二套 Schema。
- Prompt 使用 typed input/output schema、version 和 test manifest。
- 本地媒体、模型权重、数据库文件和 secrets 不进入 Git。
- demo/benchmark 大媒体通过 Artifact/manifest 引用；当前仓库文件可在迁移时登记。

---

## 6. 测试归属

- Unit 测 domain rules，无外部服务。
- Contract 测 Schema 兼容、API/provider conformance。
- Integration 使用 PostgreSQL/Temporal/ObjectStore/FFmpeg 真实组件。
- Workflow replay 使用冻结 histories。
- Golden 测 timeline、ASS、audio/video frames 和 benchmark 输出。
- Failure injection 测 crash、timeout、OOM、disk、rate limit 和 stale version。

模块自己的测试靠近 package；跨模块测试集中在根 `tests/`。

---

## 7. 并发开发规则

团队可以并行开发 Adapter、UI 和 benchmark，但必须先合并 Contract/port。每个 Work Package 只拥有自己的 package，不跨目录直接改另一个域内部表或私有类。

共享 Contract 变更需要 owner review、兼容说明和生成物更新。跨 package 循环依赖由 CI architecture test 阻断。

---

## 8. 测试与验收

- 所有 Stage 模块有明确 package owner。
- `apps` 只做 composition/transport，不含业务规则。
- Domain package 可在无 FastAPI/Temporal/模型 SDK 情况下单测。
- Worker 可按 queue 独立启动。
- 前端只能通过 OpenAPI/媒体接口访问数据。
- architecture import test 证明依赖方向无环。
