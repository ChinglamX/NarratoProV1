# Stage 2 — Full Drama Intelligence

Version: 1.0

## 1. 目标

把合法的单集或多集短剧资产转换为可定位、可校正、可增量重算的 Media Catalog、Fact Database、Character Graph 和 Approved Story Graph。

本阶段交付的是生产级剧情理解基础，不是“一次生成一段摘要”。系统必须能够回答：谁在什么时间出现、说了什么、做了什么、证据在哪里、哪些结论存在冲突、人工修正后哪些下游结果需要重算。

---

## 2. 组件拓扑

```text
Source Assets + Rights + Episode Manifest
                    │
                    ▼
        Ingest / Probe / Normalize / Proxy
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   Shot & Frame Index    Audio & Speech Index
          │                   │
          ├──── Perception Providers ────┐
          │ OCR / Detection / VLM / ASR  │
          └──────────────┬────────────────┘
                         ▼
              Observation / Evidence Store
                         │
              Identity & Temporal Fusion
                         │
                         ▼
                    Fact Store
                         │
                         ▼
        Event → State → Causal → Arc Workflows
                         │
              Conflict / Story Review Gate
                         │
                         ▼
                 Approved Story Version
```

所有步骤由 Temporal 编排；模型内部推理图可以使用 LangGraph。PostgreSQL 保存结构化元数据，Object Store 保存代理媒体、帧、原始 Provider 响应和大体积结果。

---

## 3. 设计文件

- `01_MEDIA_INGEST_AND_CATALOG.md`
- `02_AUDIO_SPEECH_PIPELINE.md`
- `03_VISUAL_PERCEPTION_PIPELINE.md`
- `04_IDENTITY_AND_FACT_FUSION.md`
- `05_STORY_REASONING_WORKFLOW.md`
- `06_PROVIDER_BENCHMARK_AND_CONFIDENCE.md`
- `07_RESOURCE_INCREMENTAL_AND_REVIEW.md`
- `08_ACCEPTANCE_AND_BUILD_ORDER.md`

---

## 4. 输入

- Source Asset ArtifactRef 与 checksum
- Rights Metadata
- Episode Manifest；缺失时允许建立待确认的顺序候选
- Language Profile、热词与角色先验；均可为空
- Provider Config、Resource Profile、Automation Policy
- Stage 1 的 Artifact、Workflow、Review 和 Observability 能力

---

## 5. 输出

- Media Catalog 与统一源时间坐标
- Scene/Shot/FrameSample/AudioSegment
- Transcript、OCR、Person/Object/Face/Speaker observations
- Source Quality Features
- Character/Identity Graph 与冲突集合
- Fact Database 与 Evidence Links
- Event、State、Relationship、Causal Edge、Arc
- Confidence Shadow Report、Provider Benchmark Report
- Approved Story Version 与完整 lineage

---

## 6. 非目标

- 不生成营销 Strategy、Hook 或成片 Timeline。
- 不根据素材质量删除剧情证据。
- 不把表演质量、潜台词或人物动机当作确定性 Fact。
- 不因模型声称“高置信度”而自动批准 Story。
- 不在缺少项目标注集时宣称人物、剧情或置信度达到生产准确率。

---

## 7. 强制不变量

- 所有时间范围回指原始 Source Asset，不以代理文件时间码取代源时间码。
- 原始观察、融合 Fact、Story 推理分层保存，禁止互相覆盖。
- 每个关键 Event 至少有一个可打开的 Evidence Link。
- 人物 merge/split、Episode 顺序与 Story Correction 均可逆且触发精准失效。
- Provider 原始响应保留为 debug artifact，正式下游只读取项目 Contract。
- 不可用、冲突和低证据必须显式表达；禁止静默丢弃或编造补齐。

---

## 8. 阶段验收摘要

- Media、Speech、Visual、Identity、Fact 和 Story 分层测试，禁止用单一总体准确率替代。
- 关键 Event Evidence coverage、严重剧情错误率和跨集身份错误率达到版本化 Quality Profile。
- 人物 merge/split、关键对白和 Story Correction 可逆并只重算依赖闭包。
- 多集并发、Worker 中断、OOM、磁盘水位、云端限流和预算耗尽均有可复现测试。
- Provider/模型/Prompt/Config 可回切，历史 artifact、lineage 和 Approval 不被覆盖。
- 未经校准的 Confidence 保持 shadow，Story Gate 仍由人工决定。

完整构建顺序和验收矩阵见 `08_ACCEPTANCE_AND_BUILD_ORDER.md`。
