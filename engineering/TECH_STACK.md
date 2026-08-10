# Technical Stack Specification

Version: 2.0

## 1. 技术战略

目标是构建高质量、生产级、可持续演进的 AI 短剧营销系统。

优先级：

1. 内容正确性与质量
2. 可靠性与可恢复性
3. 可维护、可观测和可测试
4. 模型、配置和基础设施可替换
5. 性能与成本可控

详细工具比较与限制见 `design/architecture/08_TECHNOLOGY_MATRIX.md`。

---

## 2. 语言

- Python：主要业务、AI、媒体编排和数据模型。
- TypeScript/React：Review Workspace 和专业 Timeline UI。
- Go：只有在经过性能基准后，用于高并发网关或专用服务；不作为默认要求。

Node.js 不作为核心媒体计算层，但允许用于高质量 Web UI 工具链。

---

## 3. 编排

### Temporal

生产主工作流引擎。负责耐久执行、Activity、重试、超时、heartbeat、Signal/Update、人工等待和跨机器 Task Queue。

### LangGraph

AI 推理子流程。负责 typed state、条件路由、工具循环和人工 interrupt；作为 Temporal Activity 内部组件，不负责 FFmpeg/模型 Worker 的全局资源调度。

禁止同时维护第二套自研生产状态机。

---

## 4. API 与数据契约

- FastAPI：服务 API。
- Pydantic v2 / JSON Schema：运行时与跨语言契约。
- SQLAlchemy + Alembic：数据库访问和迁移。
- OpenAPI：客户端生成与接口审计。

破坏兼容性的 Contract 必须升级 schema_version 并提供迁移。

---

## 5. 数据与存储

- PostgreSQL：Project、Run、Artifact、Dependency、Fact/Story metadata、Policy、Review、Correction、Experiment。
- pgvector：首选向量检索；用项目 recall/latency benchmark 决定是否需要独立向量库。
- ObjectStore interface：媒体 blob；单机使用文件系统实现，扩展时切换 S3-compatible backend。
- Parquet + DuckDB：离线 benchmark、反馈和性能分析。
- MLflow：模型、Prompt 和评测候选版本；不取代项目 Artifact Registry。

---

## 6. Timeline 与媒体

- 项目强类型 Master Timeline：唯一成片时间真相源。
- OpenTimelineIO：Timeline 导入导出和编辑交换。
- FFmpeg/FFprobe：解复用、代理、滤镜、混音、字幕、编码和技术探测。
- OpenCV：视觉分析、裁切轨迹和质量验证。
- ASS + libass：生产字幕描述和服务端渲染。

OTIO 不保存媒体，FFmpeg 不拥有业务 Timeline，二者均通过 Artifact/Timeline adapter 使用。

---

## 7. Intelligence Providers

所有模型通过 Provider Interface 接入，不在业务代码写死模型：

- Scene：PySceneDetect 基线；TransNetV2 等作为 benchmark 候选。
- 中文 ASR：FunASR 候选；Whisper/faster-whisper 作为回退与对照。
- Alignment/Diarization：WhisperX/其他 provider，按语言和项目样本评测。
- OCR：PaddleOCR 候选。
- Detection/Tracking/Identity：固定类、开放词汇、tracking 和 embedding 分 provider。
- VLM/LLM/Embedding：本地和云端通过同一 Schema、Evidence 和 benchmark 路由。

代码许可证与模型权重许可证分别审核。InsightFace 官方预训练模型等非商业限制资产不能成为默认生产依赖。

---

## 8. TTS 与音频

- IndexTTS2、CosyVoice、商业 TTS 进入同一 bake-off，不预先锁定唯一方案。
- Provider 准入同时评价中文发音、情感、时长、音色一致性、吞吐、硬件、成本和许可证。
- FFmpeg filtergraph 执行原声、解说、BGM、SFX、Ducking、响度和 True Peak 处理。
- Platform Profile 定义目标响度；EBU R128/ITU-R BS.1770 用作测量参考，不机械套用广播目标。

音色克隆必须有授权。

---

## 9. 可观测性

- OpenTelemetry：trace、metrics 和上下文传播。
- Prometheus：运行指标和告警数据。
- Grafana：dashboard 与 alert。
- Structured JSON logs：与 trace_id/project_id/run_id/artifact_id 关联。

禁止把高基数 artifact_id 直接用作 Prometheus label。

---

## 10. 并发与资源

- Temporal Task Queue：CPU media、CPU ML、vision、audio、cloud model、render 分资源队列。
- asyncio：I/O 和 API 调用。
- subprocess/process：FFmpeg 和本地重计算。
- model micro-batching：ASR/OCR/VLM/Embedding。
- Resource Profile：声明硬件、模型、量化、并发、超时、磁盘和成本上限。

支持并发不代表无限并发。调度必须具备 admission、backpressure、OOM 防护和公平性。

Ray、Kubernetes、独立向量数据库只在基准证明单机/当前组件不足时引入。

---

## 11. 部署

### 单机生产

- Docker Compose 运行 PostgreSQL、Temporal、API、OTel、Prometheus/Grafana。
- 媒体和模型 Worker 可在宿主机运行，以利用 VideoToolbox、Metal/MLX 或本地 GPU。
- 生产数据、缓存和临时目录分离。

### 多机扩展

- API、Temporal Worker、模型 Worker、Render Worker 独立扩展。
- Object Storage 作为共享媒体层。
- Task Queue 使用能力标签，不绑定机器地址。

---

## 12. 技术准入

每个工具/模型必须记录：

- version/checksum
- code license/model license
- supported hardware
- project benchmark
- resource/cost profile
- known limitations
- rollback provider

“开源”不等于“允许商用”，“SOTA”不等于“适合本项目生产”。
