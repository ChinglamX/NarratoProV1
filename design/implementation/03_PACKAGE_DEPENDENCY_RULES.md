# Package Dependency Rules

Version: 1.0

## 1. 目标

冻结包之间的合法依赖、调用方式和真相源，防止模块化单体退化为共享数据库和任意 import 的大模块。

输入：Repository Layout、Domain/Artifact/Workflow 设计。

输出：Dependency Graph、Allowed Imports、Port/Event Rules、Architecture Tests。

---

## 2. 依赖层次

```text
foundation ← contracts
     ↑           ↑
     ├──── domain packages ────┐
     │                          │
artifacts/timeline        application use cases
     ↑                          ↑
persistence/providers/observability adapters
                 ↑
          apps + workflows
```

更准确规则：

- `foundation` 不依赖任何业务 package。
- `contracts` 只依赖 foundation 类型，不依赖应用/adapter。
- 业务 domain 可依赖 foundation、contracts 的稳定 value objects，以及批准的 artifacts/timeline ports。
- application 可依赖本 domain 和其他 domain 的 public ports/contracts。
- adapters 依赖对应 port 和外部库。
- apps/workflows 负责组装，可依赖 application/adapters，不被 domain 反向依赖。

---

## 3. 域间依赖

```text
control ───────────────┐
intelligence → strategy → production → evaluation
       │          │          ↑             │
       └──────────┴──→ timeline ←──────────┘
artifacts/contracts/foundation serve all domains
```

这里箭头表示读取公共 Contract/Port，不允许读取对方数据库模型。Evaluation 可读各域 Artifact 并产生 Quality/Correction；不能反向覆盖任何域实体。

Control 编排所有域，但不包含域算法。Timeline 被 production 使用；Intelligence/Strategy 不依赖 Timeline 实现。

---

## 4. 真相源与写权限

| 数据 | 唯一写入所有者 | 其他模块 |
|---|---|---|
| Project/Run/Policy/Review | control | command/query |
| Artifact/Dependency/Blob | artifacts | registry port |
| Master Timeline/Patch | timeline | proposal/query |
| Observation/Fact/Story | intelligence | query/correction command |
| Strategy/Hook/Brief/Variant | strategy | query/correction command |
| Voice/Mix/Subtitle/Render | production | query/correction command |
| Quality/Calibration/Experiment | evaluation | query/proposal |
| Workflow history | Temporal | signal/query only |

SQLAlchemy table model 不得作为跨域 Contract 导入。

---

## 5. 同步与异步调用

同步 application port 用于短时、无副作用查询和同事务的本域规则。跨域长任务通过 Temporal Workflow/Activity 和 ArtifactRef。

Domain Event 用于已提交事实通知，例如 `ArtifactCommitted`、`ReviewDecided`、`TimelineSuperseded`、`PolicyActivated`。Event 不是跨域分布式事务；消费者幂等并可从真相源重建。

Command 表达意图，可失败；Event 表达已经发生的事实，不使用过去式 Event 发起操作。

---

## 6. 禁止依赖

- Domain import FastAPI/Temporal/SQLAlchemy/具体模型 SDK。
- UI 访问数据库、Object Store 私有路径或 Temporal 内部 history。
- Provider Adapter 调用 Review/Policy 数据库。
- Evaluation 直接更新 Fact/Story/Timeline/Production 表。
- Workflow 保存大媒体、模型响应或完整领域对象到 history。
- 多个 package 各自定义 ArtifactRef、RationalTime、Confidence 或 Error。
- 通过共享 `utils.py` 隐藏跨域逻辑。

---

## 7. Architecture Tests

CI 使用 import graph/AST rules 验证：

- domain 层禁止外部 framework imports；
- package 白名单依赖；
- 无循环 import；
- persistence models 不被 domain/其他域导入；
- Provider 必须实现公共 Protocol；
- Contract 名称在 Catalog 唯一；
- API DTO 与 domain object 有显式 mapper。

工具可选 import-linter/自定义静态测试，先以明确规则为准。

---

## 8. 测试与验收

- 对每条禁止规则提供一个应失败 fixture。
- Domain tests 无外部服务可运行。
- 替换一个 Provider 不改业务 use case。
- Artifact/Event consumer 重复投递保持幂等。
- Evaluation Correction 只能通过目标域 command 产生新版本。
- 删除任何未声明的跨域 import 不影响公共契约。

