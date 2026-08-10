# Production Capability Roadmap

Version: 3.0

完整阶段推演见 `design/architecture/07_IMPLEMENTATION_STAGES.md`。

跨阶段 Repository、API、Schema、Workflow、Epic 与首批任务见 `design/implementation/README.md`。

贯穿 Stage 1–6 的数据、Benchmark、Confidence 与自动化校准计划见 `design/calibration/README.md`。

项目上下文、当前恢复点和跨会话持续性由 `PROJECT_INDEX.md`、`PROJECT_STATE.md` 与 `agent/CONTEXT_RECONSTRUCTION_PROTOCOL.md` 管理，禁止依赖单一 Agent 会话。

## 1. 路线原则

本项目不建设用于验证“能否生成视频”的 MVP。基础生产链已经在 NarratoPro 项目验证，本项目直接面向更高质量和生产级运行。

阶段编号表示设计与交付顺序，不表示低质量产品版本。每个阶段必须：

- 使用最终可演进的数据契约，不创建一次性 Schema
- 满足生产级错误处理、幂等、恢复、追踪和回滚要求
- 具备独立测试、基准评测和明确验收标准
- 保持模型、配置和供应商可替换
- 产物可以被后续阶段直接复用，不进行推倒重来
- 继承 NarratoPro 已验证能力前先做兼容性和质量审计，禁止无意义重写

---

## Stage 1 — Production Foundation

详细设计入口：`design/stage1/README.md`。

目标：建立最终系统所需的生产基础，而不是重复实现视频生成 demo。

设计范围：

- Project、Run、Variant、Artifact 和依赖图
- 最终版 Artifact Envelope 与 Schema Versioning
- Evidence Link、Correction Record、Confidence Record
- Automation Policy、Resource Profile、Rights Metadata
- Master Timeline / EDL 与统一 timebase
- 幂等执行、缓存、断点恢复、失效传播和回滚
- 日志、指标、成本、审计与错误分类
- Review Workspace 所需的修改与审批接口
- NarratoPro 既有能力适配层

生产验收：

- 任一产物可追溯到输入、模型、Prompt、配置和执行环境
- 上游修订能精确失效受影响下游，不全量重跑
- 任务中断后可恢复，重复执行不会产生重复正式产物
- 数据迁移、兼容性和回滚路径经过测试
- 权利不明资产无法进入发布流程

自动化目标：L1，Confidence 进入 Shadow Evaluation。

---

## Stage 2 — Full Drama Intelligence

详细设计入口：`design/stage2/README.md`。

目标：对完整单集或多集短剧建立生产级事实与故事智能。

设计范围：

- Media Catalog、Episode、Scene、Shot、Frame
- ASR、Speaker、Person、Entity、OCR、Action
- 跨集身份解析、人物状态和全剧时间线
- Event、Relationship、Conflict、Turning Point、Climax、Story Arc
- Fact / Inference 分离与 Evidence Links
- Source Quality Features，不破坏剧情证据
- 人工纠错、冲突处理和 Story Approval
- 针对完整短剧的增量分析与复用

生产验收：

- 关键 Story 结论具有可定位证据
- 跨集人物和事件关系可人工纠正并保留历史
- 低质量素材不会从剧情理解链中丢失
- 固定评测集上的严重剧情错误率达到项目阈值
- 模型替换不改变对外数据契约

自动化目标：Story Gate 保持人工决定；低风险确定性模块在校准达标后可试点 L2。

---

## Stage 3 — Marketing Intelligence

详细设计入口：`design/stage3/README.md`。

目标：基于完整剧情资产产生可解释、可比较的高质量营销决策。

设计范围：

- Genre Config 的硬约束、软偏好、适用范围和验证数据
- 卖点、高价值事件和目标受众
- 多策略、多时长、多平台 Variant Plan
- Hook Candidate 生成、证据、理由和先验评分
- Strategy / Hook 人工对比与选择
- 结构化 Strategy 修正数据
- 无线上数据时禁止伪称效果预测

生产验收：

- 所有策略与 Hook 可以追溯到 Story 和 Evidence
- 不同类型差异来自版本化配置而非代码分支
- 人工可以比较候选差异、成本和风险
- Strategy 修订能精确触发 Timeline 重新规划
- 在基准样本上达到明确的人工一致性和质量阈值

自动化目标：L1 为默认；经过校准的候选排序可辅助人工，不自动替代创意决策。

---

## Stage 4 — Creative Timeline Engineering

详细设计入口：`design/stage4/README.md`。

目标：把视觉、节奏和解说共同编译为达到 demo 或更高目标的专业 Master Timeline。

设计范围：

- 智能横转竖、主体跟随、多人物构图和裁切关键帧
- 原片内嵌字幕检测与保留、遮罩、裁切或修复策略
- Visual Direction、Rhythm Engineering、Narration Engineering 协同规划
- 情绪曲线、信息密度、镜头时长、高潮和呼吸点
- 解说证据约束、口语风格、情绪、语速和停顿
- 人物卡、身份标签、强调字幕和 Ending Card 意图
- Timeline 编辑、版本比较和局部重新生成

生产验收：

- 画面、解说、节奏和包装使用同一 timebase
- 任一镜头与解说可回溯到原素材和剧情证据
- Timeline 修改不会造成静默错位
- demo benchmark 的节奏、解说和视觉维度达到项目阈值
- 人工可以精确修改镜头、文本、停顿和包装元素

自动化目标：AI 生成候选，人工负责创意方向和关键节奏选择。

---

## Stage 5 — Production Audio, Subtitle & Rendering

详细设计入口：`design/stage5/README.md`。

目标：以生产级媒体工程完成专业声音、字幕和稳定渲染。

设计范围：

- 可替换 TTS、情感参数、强制对齐与实际时长回写
- 原声、解说、BGM、SFX、Ducking、混音和响度
- 字幕断句、同步、安全区、重点词、多层样式和动画
- BGM、音效、字体、音色的权利与来源管理
- FFmpeg 渲染图、硬件加速、缓存、重试和质量探测
- 多格式、多版本并行生产
- 与 NarratoPro 已验证媒体能力的复用和升级

生产验收：

- 同步、响度、字幕和平台规格通过机器检查
- TTS 或镜头时长变化正确触发相关轨道重对齐
- 渲染可恢复、幂等且结果可追踪
- 任一外部资产具有明确权利状态
- 最终成片通过 demo benchmark 与人工 Release Review

自动化目标：机械检查和稳定媒体处理逐步达到 L3；Release 始终由人决定。

---

## Stage 6 — Quality Automation & Feedback Intelligence

详细设计入口：`design/stage6/README.md`。

校准数据从 Stage 1 起采集；首个 Calibration Pack 与持续运营规范见 `design/calibration/README.md`，不得等到 Stage 6 才开始补数据。

目标：在不降低质量的前提下减少机械人工审核，并用反馈持续提升系统。

设计范围：

- 离线质量评分、阻断项和问题时间码定位
- Confidence 校准、严重漏检率、覆盖率和漂移监控
- Story、Strategy、Timeline、Release 的结构化修正闭环
- Prompt、模型、阈值和 Genre Config 候选版本评测
- 灰度、审批、上线、监控和回滚
- 合法线上数据与 variant_id 关联
- A/B Experiment、留存、完播、互动和策略校准

生产验收：

- 自动化升级依据校准数据和风险指标，不依据主观百分比
- 高置信度不能覆盖阻断项
- 严重错误触发自动降级
- 反馈只能产生候选优化，未经评测审批不得上线
- 线上指标不会反向改写剧情事实

自动化目标：稳定低风险模块逐步从 L2 演进到 L4；人工最终负责创意与发布决策。

---

## Research Track

研究能力可以并行验证，但未达到数据和评测要求前不能阻断生产主线：

- 演员表演质量自动评价
- 自动穿帮检测
- 无历史数据的 Hook 效果预测
- 高级情感理解和潜台词推断
- 全自动类型识别
- 全自动发布
