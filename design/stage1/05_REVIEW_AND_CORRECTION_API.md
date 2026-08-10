# Stage 1 Review and Correction API

Version: 1.0

## 1. 目标

提供稳定的审核和结构化修订后端，使后续 Story、Strategy、Timeline、Release UI 使用同一套并发、版本和审计机制。

---

## 2. API 原则

- Command/Query 分离。
- 所有写操作要求 Idempotency-Key。
- 所有修改要求 expected target version。
- API 不直接修改 Artifact payload；提交 Patch/Correction 生成新版本。
- 返回 machine-readable error code。

---

## 3. Review API

### Create Review Request

`POST /v1/projects/{project_id}/reviews`

输入：gate、target ArtifactRef、policy ref、context refs。

输出：review_id、state=awaiting_review、workflow_id。

通常由 Workflow Activity 调用，人工客户端无权为任意 artifact 创建 Release Gate。

### Get Review Package

`GET /v1/reviews/{review_id}`

输出：target、evidence、quality issues、diff、policy、available actions。

### Submit Decision

`POST /v1/reviews/{review_id}/decision`

```yaml
expected_target_version: integer
decision: approve | revise | reject
reasons: [object]
requested_changes: [object]
```

冲突：已决定、target 已 superseded、版本不匹配。

---

## 4. Correction API

### Submit Artifact Patch

`POST /v1/artifacts/{artifact_id}/patches`

输入：base version、semantic operations、reason。

输出：patch_id、new ArtifactRef、invalidation summary。

### Preview Impact

`POST /v1/artifacts/{artifact_id}/patches:preview`

不写入，返回：验证错误、冲突、将失效的 downstream、预计重算和成本。

### Timeline Patch

`POST /v1/timelines/{timeline_id}/patches`

使用 Timeline semantic operations，不接受客户端上传整个 Timeline 覆盖服务器版本。

---

## 5. Correction Taxonomy

- identity_merge / identity_split / identity_name
- fact_value / fact_time / fact_source
- story_event / story_causality / story_order
- strategy_direction / hook_select / duration
- timeline_trim / move / replace / crop / retime
- narration_text / emotion / pronunciation / pause
- audio_gain / bgm / sfx / ducking
- subtitle_text / timing / style / position
- rights / technical / other

每个类型定义 payload Schema 和失效规则。

---

## 6. Temporal 协调

Decision 数据库事务提交成功后发送 Signal。若 Signal 失败：

- API 返回 accepted，并标记 delivery_pending。
- outbox/reconciler 重试 Signal。
- Workflow 收到重复 Signal 时按 review_id 去重。

不使用“先 Signal 后写数据库”，避免 Workflow 前进但审计记录丢失。

---

## 7. 权限

- Viewer：读取。
- Editor：提交非 Release correction。
- Reviewer：Story/Strategy/Timeline decision。
- Release Approver：Release decision。
- Admin：Policy/Role 管理。

Release Approver 与自动化服务账号分离。每次决定保存身份和权限快照。

---

## 8. 并发与冲突

- 两人审核同一 request：第一个最终 decision 成功，第二个得到 AlreadyDecided。
- 两人修改同一 artifact：基于 expected version；可合并 Patch 显示 rebase，冲突项人工选择。
- 审核期间上游变化：review_request 标记 stale，禁止批准旧版本。

---

## 9. 数据最小化

Review Package 只返回必要媒体代理、时间片和业务字段；签名 URL 有短有效期。敏感人脸、音色和未发布内容遵守访问审计。

---

## 10. 测试

- Idempotency-Key 重放。
- stale target 不能批准。
- Decision DB 成功/Signal 失败可恢复。
- Patch preview 与 commit impact 一致。
- RBAC 阻止未授权 Release。
- Correction 产生新版本和正确 invalidation。
