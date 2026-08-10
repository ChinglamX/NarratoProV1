# Intelligence Plane Detailed Design

Version: 1.0

## 1. 目标

把完整单集或多集视频转换为可验证的 Media Catalog、Fact Database、Story Graph 和 Evidence Links，为营销策略提供稳定事实基础。

---

## 2. 建设分层

```text
Media Ingest
→ Technical Probe / Proxy / Audio Demux
→ Shot / Audio Segment Index
→ Parallel Perception
→ Identity & Temporal Fusion
→ Fact Store
→ Story Reasoning
→ Conflict Detection / Human Correction
→ Approved Story Graph
```

---

## 3. Media Catalog

| 项目 | 设计 |
|---|---|
| 工具 | FFprobe/FFmpeg；PySceneDetect；可选 TransNetV2 作为对照 detector |
| 输入 | Source Media Artifact、Episode manifest |
| 输出 | Episode、Scene、Shot、FrameSample、AudioSegment、Proxy Media |
| 建设 | 先无损记录源 timebase，再生成统一代理；cut 候选保留 detector、score 和版本 |
| 并发 | Episode 并行；单视频 demux 与 probe 一次；shot detection 可按连续分块并在边界重叠 |
| 效果 | 任一后续事实可定位到源集、源时间码和帧 |

PySceneDetect 的 Content/Adaptive/Threshold 等 detector 适合作为工程基线，但复杂运镜、闪光和渐变会误检。生产系统应支持 detector ensemble、人工合并/拆分和基准集调参，不把单一算法输出当真相。

---

## 4. Speech & Audio Facts

### 工具策略

- 中文主 ASR：FunASR provider，利用 VAD、时间戳、标点和可选说话人能力。
- 精细字词对齐：WhisperX provider 或独立 forced-alignment provider。
- 备选：faster-whisper/Whisper provider，用于交叉验证和多语言回退。
- 音频事件：先以规则/轻量分类器识别音乐、哭声、撞击等；结果只作候选。

### 输入输出

输入：标准化音轨、语言提示、热词、Speaker 范围。

输出：

- VAD Segment
- Transcript Word/Sentence
- Speaker Cluster
- Audio Event
- 每个结果的时间、置信度、provider 和原始响应

### 并发

- VAD 后的非重叠 segment 可批量推理。
- Diarization 需要全局或长窗口上下文，不能简单按短 chunk 完全独立。
- 强制对齐可按句并行，但必须在合并时解决边界重叠。
- 同一模型实例使用 micro-batch；按语言和采样率分组。

### 局限

- 重叠对白、背景音乐、方言、喊叫和内录质量会降低准确率。
- Speaker diarization 只得到 cluster，不等于角色姓名。
- 字级时间戳也有误差，不能直接当作帧级剧情事实。

---

## 5. Visual Facts

| 能力 | 基线工具 | 生产设计 | 并发 | 主要局限 |
|---|---|---|---|---|
| OCR | PaddleOCR | 检测+识别+跨帧跟踪；区分原片字幕与场景文字 | Shot/采样帧并行，结果按轨迹合并 | 压缩、艺术字、运动模糊、遮挡 |
| 人/物检测 | 许可证合规 detector provider；Grounding DINO 作为开放词汇候选 | 固定类检测与开放词汇检测分开；保留 bbox/label/score | Frame micro-batch | 类别提示敏感，跨域误检 |
| Tracking | ByteTrack 类 tracker + 自研轨迹融合 | 每 Shot 内跟踪，跨 Shot 用外观/上下文重新关联 | Shot 并行；Shot 内顺序 | 遮挡、换装、多人相似 |
| 人脸/人物 | 可替换 embedding provider | 项目内临时身份；正侧脸、多模态和服装特征融合 | 检测批量；身份图聚合 | 预训练权重许可证、侧脸、年龄/妆造变化 |
| VLM 描述 | 经过项目基准和许可证审核的 VLM provider | 只分析选定关键帧/短片段；强制结构化输出和证据 | Shot/候选片段并行，API/显存限流 | 幻觉、时序理解弱、成本高 |
| Embedding | CLIP/SigLIP 类 provider | 镜头、人物、动作候选检索；模型版本独立索引 | 批量 | 相似不等于剧情相关 |

禁止把 InsightFace 官方预训练模型直接视为可商用默认：其代码许可证与官方模型权重使用条件不同。所有 provider 必须经过 Rights Registry。

---

## 6. Source Quality Features

输入：Media/Shot/Audio facts。

输出：清晰度、噪声、曝光、黑帧、冻结、构图风险、字幕遮挡、响度、削波等可测特征。

建设方式：

- 确定性指标：OpenCV/FFmpeg/音频统计。
- 学习型指标：输出 feature 与 confidence，不直接排除素材。
- “表演好不好”“是否穿帮”归 Research，不进入早期硬过滤。

并发：按 Shot 并行；结果以 Shot 和时间范围聚合。

效果：Strategy 可以优先选择高质量素材，Story 仍读取完整剧情证据。

---

## 7. Identity & Temporal Fusion

目标：把 ASR Speaker、Face Track、Person Track、OCR Name、对白称呼和 Episode 上下文融合为项目内 Character。

建设：

1. 生成局部 observation，不直接命名人物。
2. 建立 observation graph。
3. 使用确定性约束排除不可能匹配。
4. AI 提出 merge/split/name 候选和证据。
5. 高风险冲突进入 Review Workspace。

输入：Speaker/Face/Person/OCR/Dialog observations。

输出：Character、Identity Link、Conflict Set、Confidence Record。

并发：局部观察并行；全局融合按 Project 串行提交版本，计算过程可分区。

局限：跨集换装、双胞胎、遮脸、回忆镜头和角色易容必须允许人工拆分与合并。

---

## 8. Fact Store

Fact Schema 必须包含：

- subject / predicate / object 或 typed fact payload
- source time range
- observation provider
- confidence/calibration
- status：observed、disputed、corrected、superseded

模型推测的“愤怒”“嫉妒”“故意”等不能无条件写入 Fact。应记录可观察信号，再在 Story 层推理情绪和动机。

---

## 9. Story Intelligence

### 工具与建设

- LangGraph：分步骤提取 Event、因果、人物状态、关系和 Story Arc。
- PostgreSQL：Story entities、edges、versions 和 Evidence Links；不必一开始引入图数据库。
- VLM/LLM Provider：模型无关接口；本地与云端模型通过 benchmark 路由。
- pgvector：检索相关事实、相似事件和跨集线索。

### 推理流程

```text
Fact Retrieval
→ Event Candidates
→ Evidence Validation
→ Character State Diff
→ Causal Link Candidates
→ Timeline / Arc Assembly
→ Contradiction Scan
→ Story Review Package
```

每个节点输出 typed artifact，不让一个超长 Prompt 一次生成完整 Story Database。

### 输入输出

输入：Fact Database、Character Graph、Episode Timeline、Genre-neutral rules。

输出：Event、State Transition、Relationship、Causal Edge、Conflict、Turning Point、Arc、Unresolved Question。

### 并发

- Episode 内 Event 提取并行。
- Character 状态链可按 Character 并行。
- 全剧因果和 Arc 需要汇总后执行。
- 合并采用确定性排序、去重和 conflict artifact，不让并发结果最后写入覆盖。

### AI 能力边界

可自动：明显事件、对白事实、候选因果、摘要、冲突扫描。

需要人工或高风险审核：隐含动机、潜台词、复杂时间跳跃、人物身份反转、缺失镜头造成的因果。

---

## 10. 缓存与增量计算

- Media checksum 不变则复用 probe、proxy 和基础特征。
- 模型/配置变更只失效对应 provider 输出及派生节点。
- 人物 merge/split 只重算受影响 Character、Event 和 Story edges。
- Prompt 更新不重跑媒体感知层。
- Story Approval 固定一个 story_version，Strategy 必须引用准确版本。

---

## 11. 生产验收

- ASR/OCR/identity 按项目数据集分别评测，不使用单一“总体准确率”。
- 所有关键 Event 至少一个 Evidence Link。
- 严重剧情错误有明确 taxonomy 与阈值。
- 任何人物 merge/split 可撤销并重算依赖。
- 多 Episode 并发不会产生时间线乱序或身份重复提交。
- 模型不可用时有回退、人工补录或明确 unavailable，禁止编造补齐。
