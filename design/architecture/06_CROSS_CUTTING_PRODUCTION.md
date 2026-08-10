# Cross-cutting Production Design

Version: 1.0

## 1. 数据与存储

### PostgreSQL

保存 Project、Run、Artifact、Dependency、Policy、Review、Correction、Evidence Index 和 Experiment 元数据。

原则：

- 核心查询字段规范化，模型扩展信息使用 JSONB。
- Artifact 不可变；新版本新增记录。
- 使用唯一约束保证幂等，不以应用层“先查后写”代替约束。
- 大向量先使用 pgvector；只有规模和延迟基准证明不足时才引入独立向量库。

### Object Storage

保存原片、代理文件、帧、音频、模型原始输出、OTIO、字幕和成片。

- URI 不暴露物理后端。
- 临时文件、缓存和正式 artifact 分 bucket/prefix。
- 正式 artifact 开启 checksum、生命周期和备份策略。
- 数据库只保存引用与元数据，不存大媒体 blob。

### 搜索与分析

- pgvector：人物/镜头/事件语义检索。
- Parquet + DuckDB：离线评测、Correction 和性能数据分析。
- 规模扩大后再评估 ClickHouse 或独立湖仓，避免早期堆栈膨胀。

---

## 2. 数据契约

推荐：Pydantic v2 作为 Python 运行时模型，导出 JSON Schema；数据库迁移使用 Alembic；事件 Schema 必须版本化。

每个 Artifact 至少包含：

- identity/version/checksum
- producer/model/prompt/config
- immutable inputs
- Evidence/Confidence（适用时）
- rights/security classification
- created_at 与 trace_id

Master Timeline 内部模型应是 OTIO 的严格超集或可逆映射：OTIO 负责编辑交换，自定义 metadata 负责 Evidence、Narration、Rights 和生成依赖。OTIO 不保存实际媒体，媒体仍由 Artifact Registry 管理。

---

## 3. 可观测性

使用 OpenTelemetry 统一 trace 和 metrics；日志采用结构化 JSON 并关联 trace_id、project_id、run_id、stage、artifact_id。

生产指标：

- 吞吐：video_minutes_processed、artifacts_created
- 延迟：stage_duration、queue_wait、model_latency
- 质量：story_correction_rate、timeline_revision_count、blocker_rate
- 可靠性：retry_rate、terminal_failure_rate、cache_hit_rate
- 资源：CPU、内存、GPU/MLX、临时磁盘、编码速度
- 成本：tokens、API cost、compute seconds、cost_per_video_minute

Prometheus 保存运行指标，Grafana 展示和告警；长期业务评测保存在分析数据集中，不把高基数 artifact_id 直接做 Prometheus label。

---

## 4. 安全与权利

- 项目、素材和人工审核记录分级授权。
- 模型服务只获得任务所需的最小数据。
- 云端模型调用前执行敏感数据和 Rights Policy。
- BGM、SFX、字体、TTS 音色、视觉模型权重均登记许可证。
- 人脸识别属于敏感能力：默认项目内临时身份，不建立跨项目人物库。
- 生成/克隆音色必须记录授权证明和适用范围。

许可证是工具准入的一部分：例如 InsightFace 代码与其官方预训练模型许可不同，不能因为代码是 MIT 就默认模型可商用。

---

## 5. 配置与模型注册

- Git 管理静态 Schema 和默认配置。
- PostgreSQL 管理已批准的运行配置版本。
- MLflow 可用于模型、Prompt、评测集和候选版本比较，但生产别名切换必须通过项目审批流程。
- 配置分 hard constraints 与 soft preferences。
- 所有生产 Run 固定解析后的配置快照，不读取会漂移的 `latest`。

---

## 6. 测试体系

1. Contract：Schema、迁移、兼容性。
2. Unit：纯函数、时间运算、Policy、FFmpeg 参数生成。
3. Golden Media：固定小视频的 Scene、ASR、Timeline、字幕和渲染结果。
4. Model Eval：按类型、画质、口音、多人和跨集数据分层。
5. Integration：数据库、对象存储、Temporal、Worker。
6. Failure Injection：Worker kill、磁盘满、API timeout、模型 OOM。
7. Quality Benchmark：demo 与人工标注样本。
8. Load：多 Project、多 Episode、多 Variant 并发。

AI 结果不应仅做精确字符串断言；分别测试 Schema/证据等确定性要求和内容评分。

---

## 7. 部署拓扑

### 单机生产拓扑

- Docker Compose：PostgreSQL、Temporal、OTel Collector、Prometheus/Grafana、API。
- 媒体与模型 Worker 可运行在宿主机，以利用 VideoToolbox、Metal/MLX 或本地 GPU。
- 文件系统实现 ObjectStore 接口；必须支持迁移到 S3-compatible backend。

### 扩展拓扑

- API、Temporal Worker、模型 Worker、Render Worker 分开部署。
- Task Queue 绑定能力标签，不在业务代码写死机器地址。
- Object Storage 成为共享媒体层；PostgreSQL 配置备份和只读副本。

不以 Kubernetes 作为第一前提；只有机器数量、隔离和运维收益明确时引入。

---

## 8. 容量规划

所有效果声明必须绑定 Resource Profile：芯片/显存/统一内存、模型、量化、视频分钟、并发和延迟。

必须测量而不是猜测：

- 每分钟视频产生的帧、特征和临时存储
- 各模型实时因子 RTF
- 单项目峰值内存
- 多 Episode 并行的吞吐与退化
- Render 与模型竞争资源时的影响

上线前给每类 Worker 设置硬并发、内存水位、磁盘水位和预算熔断。
