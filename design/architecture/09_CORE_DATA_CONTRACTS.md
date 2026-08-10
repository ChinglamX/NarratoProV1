# Production Core Data Contracts

Version: 1.0

跨阶段完整 Artifact/Schema 名称、所有者、状态与生命周期以 `design/implementation/05_SCHEMA_AND_ARTIFACT_CATALOG.md` 为准；本文件保留核心结构示例，不另建第二套注册表。

## 1. 约定

- ID 使用不可变 UUID。
- 日期时间使用 UTC ISO-8601。
- 媒体时间使用 rational time/timebase；API 可同时提供 time_ms 便于展示。
- Artifact 不可变；修改生成新 version。
- 所有跨域输入使用 ArtifactRef，不直接读取其他模块内部表。
- 正式实现以 Pydantic/JSON Schema 和数据库约束为准。

---

## 2. Artifact Envelope

```yaml
artifact_id: uuid
artifact_type: string
schema_version: string
version: integer
project_id: uuid
run_id: uuid
variant_id: uuid | null
state: draft | awaiting_review | approved | rejected | superseded
created_at: datetime
created_by: {kind: human|model|system, id: string}
inputs: [ArtifactRef]
producer:
  module: string
  module_version: string
  model_ref: string | null
  prompt_version: string | null
  config_versions: object
  resource_profile: string
checksum: string
rights_class: string
trace_id: string
payload_uri: string | null
payload: object | null
```

约束：

- approved artifact 不能引用 rejected 输入。
- payload 与 payload_uri 至少一个存在；大 payload 使用 URI。
- checksum 对规范化 payload/blob 计算。
- 同一 artifact 的 version 单调增加，由数据库唯一约束保证。

---

## 3. ArtifactRef 与依赖

```yaml
artifact_ref: {artifact_id: uuid, version: integer, checksum: string}
dependency:
  upstream: ArtifactRef
  downstream: ArtifactRef
  dependency_type: semantic | timing | media | config | rights
  invalidation_rule: string
```

时间变化触发 timing 依赖；事实修订触发 semantic 依赖；权利变化触发 rights 依赖和 Release 重新审核。

---

## 4. Media Catalog

```yaml
media_asset:
  asset_id: uuid
  episode_id: uuid | null
  role: source | proxy | frame | original_audio | voice | bgm | sfx | render
  uri: string
  checksum: string
  technical:
    duration: RationalTime
    video: object | null
    audio: object | null
  rights: RightsMetadata

time_range:
  start: RationalTime
  duration: RationalTime

scene_or_shot:
  id: uuid
  source: ArtifactRef
  source_range: TimeRange
  detector: ProviderIdentity
  score: number | null
  status: detected | corrected | approved
```

---

## 5. Evidence 与 Confidence

```yaml
evidence_link:
  evidence_id: uuid
  source: ArtifactRef
  source_range: TimeRange | null
  frame_range: object | null
  evidence_type: dialogue | visual | ocr | audio | metadata | human_note
  excerpt: string | null

confidence:
  score: number | null
  status: shadow | calibrated | unavailable | drifted
  method: string
  calibration_version: string | null
  applicable_scope: string
  risk_class: low | medium | high
  supporting_factors: [object]
  opposing_factors: [object]
  evidence: [EvidenceLink]
```

score 不得脱离 method/scope 使用。blocker 与 risk_class 的优先级高于 score。

---

## 6. Fact Contract

```yaml
fact:
  fact_id: uuid
  fact_type: dialogue | speaker | person | entity | ocr | action | visual_signal | audio_signal
  subject_ref: string | null
  value: object
  source_range: TimeRange
  evidence: [EvidenceLink]
  provider: ProviderIdentity
  confidence: ConfidenceRecord
  status: observed | disputed | corrected | superseded
```

Fact 只表达观察。动机、因果和语义情绪进入 Story Contract。

---

## 7. Story Contract

```yaml
character:
  character_id: uuid
  display_name: string
  identity_links: [object]
  evidence: [EvidenceLink]

event:
  event_id: uuid
  order_key: string
  description: string
  participants: [uuid]
  source_range: TimeRange | null
  evidence: [EvidenceLink]
  confidence: ConfidenceRecord

story_edge:
  edge_id: uuid
  type: causes | enables | reveals | contradicts | changes_relationship | changes_state
  from_ref: uuid
  to_ref: uuid
  evidence: [EvidenceLink]
  confidence: ConfidenceRecord

story_graph:
  characters: [Character]
  events: [Event]
  edges: [StoryEdge]
  arcs: [object]
  unresolved_questions: [object]
```

关键 Event 必须有 Evidence。人工 merge/split Character 以 Correction/Patch 表达。

---

## 8. Strategy Contract

```yaml
selling_point:
  id: uuid
  type: string
  description: string
  story_refs: [uuid]
  evidence: [EvidenceLink]
  risk: string
  confidence: ConfidenceRecord

hook_candidate:
  hook_id: uuid
  hook_type: string
  visual_intent: object
  narration_or_dialogue: string
  source_refs: [uuid]
  rationale: string
  heuristic_scores: object
  confidence: ConfidenceRecord

strategy:
  objective: string
  audience_profile: string
  platform_profile: string
  target_duration: RationalTime
  genre_config_ref: string
  selected_selling_points: [uuid]
  narrative_spine: [object]
  hook_candidates: [HookCandidate]
  selected_hook_id: uuid | null
  cost_estimate: object
  risks: [object]
```

selected_hook_id 由批准后的 Strategy Decision 固定。

---

## 9. Master Timeline Contract

```yaml
master_timeline:
  timeline_id: uuid
  rate: {num: integer, den: integer}
  global_start: RationalTime
  duration: RationalTime
  tracks: [Track]
  markers: [Marker]
  dependencies: [ArtifactRef]

track:
  track_id: uuid
  kind: video | original_audio | narration | bgm | sfx | subtitle | overlay
  order: integer
  items: [TimelineItem]

timeline_item:
  item_id: uuid
  item_type: clip | gap | transition | text | effect
  timeline_range: TimeRange
  source_ref: ArtifactRef | null
  source_range: TimeRange | null
  content_ref: string | null
  parameters: object
  evidence_refs: [uuid]
  generation_dependencies: [ArtifactRef]
```

OTIO adapter 必须对 Clip/Track/Transition/Marker 可逆；项目私有字段保存于版本化 metadata namespace。

---

## 10. Timeline Patch

```yaml
timeline_patch:
  patch_id: uuid
  base_timeline: ArtifactRef
  operations:
    - op: insert | remove | move | trim | split | replace | retime | set_parameter
      target_item_id: uuid | null
      expected_item_version: integer | null
      payload: object
  author: object
  reason: string
```

Patch 使用 optimistic concurrency。base_timeline 已变化时必须 rebase 或报告 conflict，禁止静默覆盖人工修改。

---

## 11. Narration / Voice / Subtitle / Audio

```yaml
narration_line:
  line_id: uuid
  text: string
  intent: string
  evidence: [EvidenceLink]
  target_duration: RationalTime | null
  emotion: object
  pace: object
  pause: object
  pronunciation_hints: [object]

alignment_segment:
  line_id: uuid
  audio_range: TimeRange
  word_ranges: [object]
  confidence: ConfidenceRecord

subtitle_cue:
  cue_id: uuid
  source_line_id: uuid | null
  timeline_range: TimeRange
  text: string
  style_ref: string
  layout: object

audio_mix_plan:
  timeline_ref: ArtifactRef
  track_controls: [object]
  loudness_profile: string
  measurement: object | null
```

---

## 12. Review 与 Correction

```yaml
review_decision:
  review_id: uuid
  gate: story | strategy | timeline | release
  target: ArtifactRef
  decision: approve | revise | reject
  reviewer: object
  blockers: [object]
  reasons: [object]
  requested_changes: [object]

correction:
  correction_id: uuid
  target_before: ArtifactRef
  target_after: ArtifactRef
  module: string
  correction_type: string
  semantic_operation: object
  before: object
  after: object
  reason: string
  reviewer: object
```

Review Decision 不直接修改 target；Correction 必须指向新版本。

---

## 13. Policy 与资源

```yaml
automation_policy:
  policy_id: string
  version: string
  level: L0 | L1 | L2 | L3 | L4
  scope: object
  thresholds: object
  blockers: [string]
  sampling: object
  fallback: fail_closed

resource_profile:
  profile_id: string
  version: string
  capabilities: [string]
  concurrency_limits: object
  memory_limits: object
  disk_limits: object
  api_quotas: object
  cost_budget: object
```

每个 Run 保存解析后的 effective policy/profile snapshot。

---

## 14. Run 与 Activity

```yaml
run:
  run_id: uuid
  project_id: uuid
  workflow_id: string
  state: string
  automation_policy: object
  resource_profile: object
  stages: [StageExecution]
  cost: object

stage_execution:
  stage: string
  execution_key: string
  attempt: integer
  state: string
  inputs: [ArtifactRef]
  outputs: [ArtifactRef]
  queue: string
  worker: string
  heartbeat: object | null
  error: object | null
```

execution_key 对输入 checksum、模块、模型和配置版本计算，用于幂等与缓存。

---

## 15. Experiment 与 Performance

```yaml
release_record:
  variant_id: uuid
  render_ref: ArtifactRef
  platform: string
  published_at: datetime
  external_ref: string

performance_window:
  variant_id: uuid
  window_start: datetime
  window_end: datetime
  impressions: integer
  retention_3s: number | null
  avg_watch_time: number | null
  completion_rate: number | null
  engagement: object
  source: string

experiment:
  experiment_id: uuid
  hypothesis: string
  variants: [uuid]
  assignment: object
  confounders: [string]
  result: object | null
```

没有 assignment、样本和窗口定义时，只能叫 performance comparison，不能叫受控 A/B 实验。
