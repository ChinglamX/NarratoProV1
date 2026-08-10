# Stage 1 Database and Artifact Design

Version: 1.0

## 1. PostgreSQL Schema

建议逻辑 Schema：

- `core`：project、run、variant
- `artifact`：artifact、artifact_version、dependency、blob
- `workflow`：command、stage_execution、external_call
- `review`：review_request、decision、correction
- `policy`：automation_policy、resource_profile、config_snapshot
- `rights`：asset_rights、rights_manifest
- `audit`：audit_event

不按 AI 模型建立数据库 Schema，避免模型更换导致迁移。

---

## 2. 核心表

### core.project

```text
id uuid PK
name text NOT NULL
state text NOT NULL
created_at timestamptz NOT NULL
updated_at timestamptz NOT NULL
row_version bigint NOT NULL DEFAULT 1
```

### core.run

```text
id uuid PK
project_id uuid FK
workflow_id text UNIQUE NOT NULL
state text NOT NULL
automation_policy_snapshot jsonb NOT NULL
resource_profile_snapshot jsonb NOT NULL
created_at / started_at / finished_at
row_version bigint NOT NULL
```

### core.variant

```text
id uuid PK
project_id uuid FK
strategy_artifact_id uuid NULL
state text NOT NULL
label text
created_at timestamptz
```

---

## 3. Artifact 表

### artifact.artifact

```text
id uuid PK
project_id uuid FK
artifact_type text NOT NULL
created_at timestamptz NOT NULL
```

### artifact.artifact_version

```text
artifact_id uuid FK
version integer
schema_version text NOT NULL
run_id uuid FK
variant_id uuid NULL
state text NOT NULL
payload_json jsonb NULL
blob_id uuid NULL
checksum text NOT NULL
producer_json jsonb NOT NULL
rights_class text NOT NULL
trace_id text NOT NULL
created_at timestamptz NOT NULL
PRIMARY KEY (artifact_id, version)
UNIQUE (artifact_id, checksum)
```

约束：payload_json 与 blob_id 至少一个存在；同一版本只写一次；状态变化写入 state transition/audit，不修改 payload/checksum。

### artifact.blob

```text
id uuid PK
uri text UNIQUE NOT NULL
checksum text NOT NULL
size_bytes bigint NOT NULL
content_type text NOT NULL
storage_class text NOT NULL
state text NOT NULL
created_at timestamptz
UNIQUE (checksum, size_bytes)
```

### artifact.dependency

```text
upstream_artifact_id uuid
upstream_version integer
downstream_artifact_id uuid
downstream_version integer
dependency_type text
invalidation_rule text
created_at timestamptz
PRIMARY KEY (upstream_artifact_id, upstream_version,
             downstream_artifact_id, downstream_version,
             dependency_type)
CHECK (upstream_artifact_id <> downstream_artifact_id)
```

写入依赖前必须 cycle check；数据库保存边，应用服务负责带深度限制的图遍历。

---

## 4. Command 与幂等

```text
workflow.command
id uuid PK
idempotency_key text UNIQUE NOT NULL
command_type text NOT NULL
project_id uuid NULL
request_json jsonb NOT NULL
request_checksum text NOT NULL
state text NOT NULL
workflow_id text NULL
response_json jsonb NULL
created_at / completed_at
```

规则：

- 相同 idempotency_key、相同 checksum：返回原结果。
- 相同 key、不同 checksum：409 Conflict。
- API 事务先注册 command，再启动 Temporal；启动失败由 reconciler 重试。

---

## 5. Blob Commit Protocol

1. Worker 写 `tmp/{run_id}/{activity_id}`。
2. 计算 checksum、size、media probe。
3. 写 blob row，状态 staging。
4. Object Store 原子 move/copy 到 content-addressed URI。
5. 同一事务注册 artifact_version、dependency、blob state=committed。
6. 失败时 staging blob 由 sweeper 回收。

本地文件系统必须使用同文件系统 rename 才视为原子；跨存储 copy 要校验目标 checksum 后提交。

---

## 6. Artifact Version Service

```text
reserve_artifact(type, project_id) -> artifact_id
commit_version(artifact_id, expected_latest_version, payload, inputs, producer)
get_version(ArtifactRef)
list_versions(artifact_id)
supersede(ArtifactRef, reason)
```

`commit_version` 使用 compare-and-swap：expected_latest_version 匹配才创建 next version。并发冲突返回 VersionConflict，调用方 rebase，禁止自动覆盖。

---

## 7. Dependency Invalidation

输入：新 upstream version 与 semantic change set。

算法：

1. 查询直接 downstream edges。
2. 对每条 edge 执行 typed invalidation rule。
3. 产生 InvalidationDecision，不删除产物。
4. 广度优先传播并记录 visited。
5. 标记 downstream `stale/superseded`。
6. 生成 recompute plan。

示例：

- Story 修正：Strategy semantic dependency stale。
- Timeline subtitle style 修改：只失效 Subtitle Render 与 Final Render。
- TTS 时长变化：失效 Alignment、Subtitle Timing、Mix、Render。
- Rights 变化：失效 Release Approval，不重算内容。

并发：同一 project 的 invalidation 使用 project-scoped lock；不同 project 并行。传播分批提交，recompute plan 绑定 graph_version。

---

## 8. Review/Correction 表

- review_request：target ArtifactRef、gate、state、workflow_id、deadline、policy snapshot。
- decision：request_id UNIQUE、decision、reviewer、reasons、created_at。
- correction：before_ref、after_ref、semantic_operation、before/after、reason、dependency impact。

同一 review_request 只能有一个最终 decision；修改建议可以多条。

---

## 9. 索引

必须索引：

- artifact_version(run_id, state)
- artifact_version(variant_id, artifact_type)
- dependency(upstream...) / dependency(downstream...)
- review_request(workflow_id, state)
- stage_execution(run_id, stage, state)
- audit_event(project_id, created_at)

JSONB 只为明确查询路径建立索引，禁止无差别 GIN。

---

## 10. 保留与删除

- source、approved、release artifacts 默认长期保留。
- proxy/cache 按引用和 retention policy 清理。
- 删除项目先生成 deletion plan，检查 legal hold、release 和共享 blob 引用。
- Blob 只有引用计数为零且过保留期才物理删除。

---

## 11. 测试

- 并发 commit 同一 artifact 只有一个成功。
- idempotency key 冲突行为正确。
- cycle dependency 被拒绝。
- invalidation 只影响正确闭包。
- staging blob 崩溃后可回收或 reconcile。
- migration forward/backward 和旧 Schema 读取通过。

---

## 12. 数据迁移与回滚

回滚不是覆盖历史记录。Artifact、Decision、Audit Event 一旦提交即保持不可变；业务回滚通过创建新版本并把 active pointer 切回已验证版本完成。

数据库变更采用 expand / migrate / contract：

1. Expand：先增加 nullable 字段、新表或新索引，旧 Worker 仍可读写。
2. Migrate：后台幂等回填，记录游标、速率、错误与校验结果。
3. Switch：通过 feature flag 切换读路径，再切写路径。
4. Contract：至少跨过规定兼容窗口且 replay/restore 演练通过后，才删除旧结构。

回滚边界：

- Expand 阶段可直接停用新路径，不删除已写数据。
- Migrate 阶段通过游标续跑或反向迁移；禁止无审计的大批量原地改写。
- Switch 后优先回切 feature flag；若新旧写模型不等价，必须使用双写校验或补偿迁移。
- Contract 属高风险不可逆步骤，执行前必须有快照、恢复点、引用检查和审批记录。
- Artifact 回滚只改变 active/supersedes 关系，旧版本与 lineage 永久可查。

每次 migration 必须包含：兼容矩阵、容量影响、锁风险、forward plan、rollback plan、数据校验查询、负责人和最大允许停顿时间。生产演练必须证明从备份恢复后，数据库状态、Object Store checksum 和 ArtifactRef 能重新对账。
