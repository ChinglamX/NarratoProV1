# Stage 2 Acceptance and Build Order

Version: 1.0

## 1. 构建顺序

### Milestone 1 — Intelligence Contracts and Corpus

- Media/Observation/Identity/Fact/Story Schema
- Provider Interface 与 raw response artifact
- 标注规范、严重错误 taxonomy、evaluation dataset split
- source/proxy/evidence 时间映射

退出：Schema/compatibility、标注一致性和固定 evaluation manifest 通过。

### Milestone 2 — Media Catalog

- ingest、probe、checksum、rights snapshot
- proxy/audio/frame generation
- Scene/Shot baseline、FrameSamplePlan、Source Quality

退出：VFR/rotation/损坏媒体、时间映射、崩溃恢复和人工 Shot correction 通过。

### Milestone 3 — Speech Intelligence

- VAD/ASR/normalization/alignment providers
- diarization/speaker observations
- hotword、cross-provider conflict、manual correction

退出：分层 CER/关键实体/timestamp/DER 基线建立，失败回退和增量失效通过。

### Milestone 4 — Visual Intelligence

- OCR/TextTrack
- detection/Shot tracking/face and appearance observation
- embedding index、constrained VLM、supplementary sampling

退出：分层 OCR/identity/visual benchmark、显存安全和许可证准入通过。

### Milestone 5 — Identity and Fact

- observation graph、constraints、merge/split
- Evidence Bundle、Fact Store、ConflictSet
- Identity/Fact Review Workspace

退出：跨集身份可逆、冲突显式、并发 commit 和精准失效通过。

### Milestone 6 — Story Intelligence

- Event/evidence validation/state/relationship/causal/arc typed workflow
- global assembly、coverage/contradiction scan
- Story Review Package 与 Approval

退出：严重 Story 错误与 Evidence coverage 达标，Story version 可冻结和重放。

### Milestone 7 — Production Qualification

- Provider bake-off、Confidence shadow、resource/cost baseline
- failure injection、long-series load、canary/rollback
- dashboards、alerts、runbooks

退出：固定 Resource Profile 下的质量、吞吐、成本和恢复报告获批准。

---

## 2. 验收矩阵

| 维度 | 必须证明 |
|---|---|
| Media | 源身份、技术探测、时间映射、代理可重建 |
| Speech | 分层 CER/实体/timestamp/diarization，不隐藏严重错误 |
| Visual | OCR、track、identity、VLM 各自评测且可定位原帧 |
| Evidence | 关键 Event 可打开证据，支持与反对证据均保存 |
| Fact | 只含可观察结论，人工修正不覆盖历史 |
| Identity | merge/split 可逆、跨集一致、并发提交安全 |
| Story | Event/人物/时间/因果严重错误分别达标 |
| Confidence | shadow 可解释；未校准不参与自动放行 |
| Incremental | Provider/Prompt/Correction 触发精准失效 |
| Resilience | shard retry、fallback、unavailable、budget/OOM 处理 |
| Rights | 代码、模型权重、数据出境和素材权限可审计 |
| Operations | 容量、成本、trace、dashboard、runbook、rollback |

数值目标不得在没有项目评测数据时拍脑袋写死。首次 benchmark 产出 baseline 后，由版本化 Quality Profile 固定门槛；门槛变更需要依据和审批。

---

## 3. 端到端验收场景

1. 导入至少一组含多集、VFR/旋转/复杂音频的合法测试资产。
2. 生成 Catalog、Proxy、Shot、Audio/Frame plans。
3. 并行运行 Speech 与 Visual Providers，中途终止 Worker 并恢复。
4. 形成 Identity Graph、Fact Snapshot 和 conflicts。
5. 人工执行一次角色 merge/split、关键对白修正和 Shot split。
6. 验证只重算正确 dependency closure。
7. 运行分阶段 Story Workflow，注入矛盾 Fact。
8. Story Review 必须显示矛盾、证据、模型/配置和影响范围。
9. 人工批准 Story，冻结所有输入版本。
10. 用冻结版本重放，结构化结果稳定且 lineage、成本、trace 完整。

不得出现：人工直接修数据库、关键 Event 无证据、失败 shard 导致整项目丢失、旧 artifact 被覆盖、模型不可用时编造结果。

---

## 4. 性能与容量验证

工作负载覆盖短单集、长单集、多集 burst、高人物密度、高字幕密度和低质量音频。报告：

- media duration / wall time 与各 stage critical path；
- P50/P95 queue/runtime、batch fill、模型冷启动；
- CPU/RAM/VRAM/Metal/disk/network 峰值；
- 每分钟素材的本地计算与云端成本；
- cache hit、recompute fanout 和 storage growth；
- 多 Project 公平性及高水位降级行为。

个人 Mac mini 是必须形成的首个 Resource Profile，不代表所有模型必须本地运行；云端路由必须受权利、隐私、质量和预算约束。

---

## 5. 回滚与兼容

- Provider/模型/Prompt/Config 回切后，新运行读取指定旧版本；已有 artifact 不覆盖。
- Embedding 模型更换建立新索引，旧索引保留至依赖迁移完成。
- Identity/Fact/Story Correction 通过新版本和反向 Correction 撤销。
- Schema 使用 Stage 1 expand/migrate/contract，兼容窗口覆盖存量 Worker。
- Workflow 版本必须 replay 历史 Stage 2 executions。
- Story Approval 回退只能选择先前已批准版本或重新进入 Review，不能把未批准草稿设为正式输入。

---

## 6. 完成定义

- 所有 Milestone 退出条件和验收矩阵通过。
- benchmark、严重错误和资源报告均可复现。
- Confidence 仍可保持 shadow；不得为了宣称自动化而降低 Story Gate。
- 多集 Character/Story correction 和增量重算完成演练。
- Stage 3 只依赖 ApprovedStoryRef、Evidence/Fact 查询接口和稳定 Contract，不读取 Provider 私有字段。

---

## 7. 不得以此替代完成

- 有一段正确摘要不代表 Story Intelligence 成立。
- ASR 总体 CER 低不代表关键人物和否定词正确。
- 人脸相似度高不代表跨集角色身份正确。
- VLM 输出流畅不代表有证据。
- 全量重跑能修正结果不代表支持增量计算。
- 单机跑完一次不代表并发、恢复、成本和许可证达到生产标准。

