# Open-source Technology Decision Matrix

Version: 1.0

## 1. 选型规则

每项工具通过六项准入：功能、稳定性、许可证、可替换性、项目 benchmark、目标硬件性能。不存在“默认永久 SOTA”；模型类工具必须通过 provider interface 和定期 bake-off。

---

## 2. Production Foundation

| 能力 | 推荐 | 定位 | 不承担 |
|---|---|---|---|
| API | FastAPI + Pydantic | typed API、Schema、validation | 长任务执行 |
| Durable Workflow | Temporal | crash recovery、retry、timer、human wait | AI 推理质量 |
| Agent Graph | LangGraph | typed AI state、tool loop、interrupt | 媒体资源调度 |
| Metadata | PostgreSQL | ACID、版本、依赖、审核 | 大媒体 blob |
| Vector | pgvector | 初始语义检索、与业务过滤联动 | 无限规模专用向量服务 |
| Timeline | internal Schema + OpenTimelineIO | 强类型时间线+行业交换 | 实际媒体渲染 |
| Object Storage | abstract FS/S3 adapter | 媒体 blob | 业务事务 |
| Observability | OpenTelemetry + Prometheus/Grafana | traces、metrics、alerts | 长期高维业务分析 |
| Experiment | MLflow | model/prompt/eval registry | 项目 Artifact 真相源 |

---

## 3. Media & Intelligence

| 能力 | 首选候选 | 备选/对照 | 准入要点 |
|---|---|---|---|
| Probe/Render | FFmpeg/FFprobe | 无同级默认替代 | 构建版本、codec、filter、硬件加速必须记录 |
| Scene | PySceneDetect Adaptive/Content | TransNetV2 | 项目转场 benchmark；支持人工修正 |
| 中文 ASR | FunASR provider | faster-whisper/Whisper | 方言、BGM、时间戳、许可证、Mac/服务器性能 |
| Forced Alignment | WhisperX/provider | ASR 自带 timestamp + custom aligner | 中文字词对齐基准、依赖模型许可 |
| OCR | PaddleOCR | VLM OCR / other provider | 原片字幕、艺术字、竖排字、运动模糊 |
| Detection | 合规固定类 detector | Grounding DINO open-vocabulary | code/weights 分别审计；开放词汇只作候选 |
| Tracking | ByteTrack 类 provider | optical flow/custom | Shot 内有效，跨 Shot 需 identity fusion |
| Face/Identity | 可替换 embedding provider | licensed InsightFace or trained model | InsightFace 官方模型非默认商用资产 |
| VLM | benchmark-selected local/cloud provider | 多模型 bake-off | 视频时序、幻觉、成本、数据出境 |
| Embedding | CLIP/SigLIP 类 provider | VLM embedding | 版本化索引，监测 recall |

避免把 YOLO 商业许可、InsightFace 权重、TTS 音色授权等问题推迟到上线前处理。

---

## 4. Timeline & Media Production

| 能力 | 推荐 | 说明 |
|---|---|---|
| Editorial interchange | OpenTimelineIO | Clip/Track/Transition/Marker/metadata；媒体外部引用 |
| Video transforms | FFmpeg + OpenCV | FFmpeg 执行，OpenCV 分析/验证 |
| Subtitle description | ASS | 多样式、多位置、逐字效果 |
| Subtitle render | libass through FFmpeg | 服务端稳定基线 |
| TTS | IndexTTS2/CosyVoice/commercial provider bake-off | 不锁定；质量、时长、情感、硬件、许可共同评测 |
| Audio mix | FFmpeg filtergraph | loudnorm、sidechaincompress、amix 等 |
| Loudness measurement | FFmpeg loudnorm/ebur128 style metrics | 目标值由 Platform Profile 定义 |
| Preview | proxy render + browser player | 必须与 final 共用 Timeline compiler |

---

## 5. 并发实现

### 默认

- Python asyncio：I/O 和 API 调用。
- Process/subprocess：FFmpeg、CPU-heavy native tools。
- Temporal Task Queue：跨机器和耐久任务并发。
- Provider micro-batching：ASR/VLM/OCR/embedding。

### 暂不默认

- Airflow：更适合定时数据 DAG，不作为有人审长媒体 Workflow 主引擎。
- Ray：只有模型任务分布式吞吐基准证明需要时引入。
- Kubernetes：只有多机器隔离和运维收益明确时引入。
- 独立向量数据库：pgvector 基准不满足后再评估。

---

## 6. Provider Interface

所有模型 provider 统一暴露：

```text
capabilities()
validate_input()
estimate_resources()
estimate_cost()
infer()
health()
model_identity()
license_metadata()
```

输出必须是项目 Schema，原始 provider response 作为 debug artifact 保存。业务代码不得依赖某家模型特有字段。

---

## 7. Tool References

- Temporal docs: https://docs.temporal.io/
- LangGraph human-in-the-loop: https://docs.langchain.com/oss/python/langgraph/interrupts
- OpenTimelineIO: https://opentimelineio.readthedocs.io/
- OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
- FFmpeg filters: https://ffmpeg.org/ffmpeg-filters.html
- PySceneDetect detectors: https://www.scenedetect.com/docs/latest/api/detectors.html
- FunASR: https://github.com/modelscope/FunASR
- WhisperX: https://github.com/m-bain/whisperX
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- Grounding DINO: https://github.com/IDEA-Research/GroundingDINO
- InsightFace licensing note: https://github.com/deepinsight/insightface
- pgvector: https://github.com/pgvector/pgvector
- libass: https://github.com/libass/libass
- CosyVoice: https://github.com/FunAudioLLM/CosyVoice
- IndexTTS: https://github.com/index-tts/index-tts
- MLflow evaluation: https://mlflow.org/docs/latest/ml/evaluation/
- EBU loudness resources: https://tech.ebu.ch/loudness/
