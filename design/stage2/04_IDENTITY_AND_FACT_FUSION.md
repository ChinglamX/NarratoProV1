# Identity and Fact Fusion

Version: 1.0

## 1. 目标

把 Speaker、Face、Person Track、OCR 名称、对白称呼和时空上下文融合成项目内 Character Identity，并把多模态 Observation 转换为可观察、可冲突、可修正的 Fact。

输入：Speech/Visual/OCR observations、Episode/Shot catalog、人工先验与 Correction。

输出：CharacterIdentity、IdentityLink、ConflictSet、Fact、EvidenceBundle、FusionReport。

---

## 2. 数据分层

```text
Observation（Provider 原始观察）
  → Candidate Link（可能同一对象）
  → Identity Graph（项目内身份）
  → Fact（经过融合的可观察事实）
  → Story Interpretation（另一个模块）
```

Observation 永不因融合而删除。Identity merge/split 产生新 graph version。Fact 引用 observation/evidence，不复制无法验证的自然语言结论。

---

## 3. Identity Graph

节点：FaceObservation、PersonTracklet、SpeakerCluster、NameMention、KnownCharacterSeed、Character。

边：same_candidate、cannot_be_same、speaks_as、visible_during、named_as、corrected_same、corrected_different。

硬约束示例：

- 同时出现在互斥空间中的两个 Tracklet 不能合并；
- 同一时刻多个清晰不同人脸不能共享单一实体；
- 人工 `corrected_different` 优先于模型相似度；
- 回忆、梦境、变装和双胞胎只产生风险标记，不硬编码结论。

软证据：face similarity、appearance、speaker embedding、唇动/语音重叠、对白称呼、相邻 Shot 连续性。权重由版本化 Fusion Config 管理。

---

## 4. 融合流程

1. 按 Episode/Shot 构建局部 observation graph。
2. 应用确定性 cannot-link 和人工约束。
3. 计算候选边特征，不立即提交 merge。
4. 生成局部 cluster 与冲突。
5. 跨集汇总，用锚点角色和证据提出 merge/split proposal。
6. 对高风险、近阈值和冲突候选生成 Review Package。
7. CAS 提交新 Identity Graph version，触发受影响 Fact/Story 失效。

计算可按 Episode/Character component 并行；全局 graph commit 对 Project 串行，避免竞态产生重复 Character。

---

## 5. Fact 类型与约束

Fact 只描述观察：

- dialogue：某时间范围存在某段语音文本；
- speaker：SpeakerObservation 与 Character 的关联候选/批准结果；
- person/entity：人物或物体可见；
- ocr：某区域可见某文本；
- action：可观察动作及参与对象；
- visual_signal/audio_signal：表情、姿态、哭声、撞击等信号。

禁止直接写入 Fact：动机、因果、关系变化、道德判断和类型化营销标签。

每条 Fact 必须有 source range、EvidenceLink、ProviderIdentity、ConfidenceRecord、status 和 schema version。人工修正写 `corrected` 新版本，旧 Fact 标记 superseded 但保持可查。

---

## 6. 多模态 Evidence Bundle

Evidence Bundle 聚合同一时间窗口、实体和命题相关的多源证据，保留 supporting/opposing 两侧。例如“角色 A 说某句对白”可同时包含音频 speaker、画面 lip activity、字幕 OCR 和上下 Shot identity。

跨源一致性提高的是融合可信度，不等于来源完全独立。原片字幕与音轨可能来自同一脚本，Confidence 方法必须记录相关性假设，避免重复计票。

---

## 7. 冲突与修正

ConflictSet 包含冲突命题、涉及 observation/fact、严重度、可选解释、推荐补采和 reviewer 操作。支持：

- merge characters；
- split character；
- assign/unassign name；
- correct transcript/OCR；
- accept/reject fact；
- mark unresolved。

Correction 必须生成 dependency impact preview。用户确认后才提交新版本；撤销通过反向 Correction 创建后继版本，不删除审计历史。

---

## 8. 测试与验收

- 同脸不同角色、双胞胎、换装、回忆、遮脸和多人同框。
- 同时说话、画外音、旁白和嘴型不可见。
- 人工 merge/split 连续往返后 lineage 与依赖图正确。
- 两个并发 reviewer 修改同一 graph 时 stale version 被拒绝。
- supporting/opposing evidence 都能从 Review Workspace 打开到源时间码。
- 无法解析身份时保留临时 Character，不强制命名。

