# Stage 1 Master Timeline and OTIO Design

Version: 1.0

## 1. 目标

建立最终生产系统使用的 Timeline Core：统一 timebase、immutable version、semantic patch、冲突检测、依赖失效和 OTIO 交换。

---

## 2. 内部模型

```text
Timeline
 ├─ rate / global_start / duration
 ├─ Track[]
 │   └─ Item[]: Clip | Gap | Transition | Text | Effect
 ├─ Marker[]
 └─ Dependency[]
```

时间使用 RationalTime：`value:int64 + rate_num/rate_den`。禁止以浮点秒作为持久化真相。

---

## 3. Track 约束

- video/audio 轨按时间排序。
- 普通 Clip 不重叠；Transition 明确声明 overlap handles。
- subtitle/overlay 可以重叠，但需 z-order 和 collision policy。
- source range 不得越出 Media Asset available range。
- item_id 在 Timeline 生命周期内稳定。

---

## 4. Timeline Patch

操作：

- insert/remove/move
- trim/split/replace
- retime
- set_parameter
- attach/detach_dependency

每个 Patch 包含 base TimelineRef 和 expected item revisions。

应用流程：

1. 读取 base version。
2. 验证 preconditions。
3. 纯函数应用 operations。
4. 执行 Timeline Validator。
5. 计算 ChangeSet。
6. Commit 新 artifact version。
7. 触发 dependency invalidation。

同一 base 的并发 Patch 若修改不同 item 可尝试语义 rebase；同一 item 冲突返回 Conflict，必须人工或上层 planner 处理。

---

## 5. Validator

检查：

- rational time 合法
- item range 和 source handle
- video track overlap
- transition handles
- dangling media/content refs
- unsupported effect/parameter
- target duration/profile
- dependency version 是否 stale

Validator 分 error/warning；error 禁止 commit render-ready Timeline。

---

## 6. OTIO 映射

| Internal | OTIO |
|---|---|
| Timeline | otio.schema.Timeline |
| Track | otio.schema.Track |
| Media Clip | otio.schema.Clip + MediaReference |
| Gap | otio.schema.Gap |
| Transition | otio.schema.Transition |
| Marker | otio.schema.Marker |
| Text/Effect | metadata + custom SchemaDef/adapter |

项目 metadata namespace：`com.narratopro.v1`。

必须保存：artifact refs、evidence refs、item id、generation dependencies、rights refs。OTIO 不支持的生产字段不能无提示丢弃；adapter 输出 LossReport。

---

## 7. Round-trip

```text
Internal Timeline
→ OTIO export
→ OTIO parse/import
→ Internal Timeline
→ semantic diff
```

核心 Clip/Track/Range/Transition 必须无损。第三方编辑器可能删除私有 metadata，因此导入时必须报告 missing metadata，并禁止直接覆盖 approved Timeline。

---

## 8. Render Plan Interface

Stage 1 只定义接口：

```yaml
render_plan:
  timeline_ref: ArtifactRef
  platform_profile_ref: ArtifactRef
  resolved_assets: [ArtifactRef]
  operations: [typed media operation]
  expected_output: object
```

Render compiler 是纯函数：同一 Timeline/Profile/Toolchain 产生相同 Render Plan checksum。

---

## 9. 并发

- 不同 Timeline/Variant 可并行。
- 同一 Timeline 使用 optimistic concurrency。
- Validator 和 OTIO export 为无状态计算，可横向扩展。
- Commit 与 invalidation 使用 project graph_version 保证一致性。

---

## 10. 测试

- NTSC/30fps/25fps/variable source 的 rational conversion。
- trim/split/transition handle 边界。
- 并发 Patch 冲突和可 rebase 情况。
- OTIO round-trip 与 LossReport。
- Timeline 改动的依赖失效矩阵。
- 大 Timeline 序列化性能与 Schema migration。
