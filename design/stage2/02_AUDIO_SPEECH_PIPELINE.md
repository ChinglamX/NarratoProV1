# Audio and Speech Pipeline

Version: 1.0

## 1. 目标

从源音轨产生可追溯的语音区间、文本、字词时间、说话人 cluster 和音频事件候选。Speaker Cluster 与角色姓名严格分离。

输入：AudioStem、Language Profile、Hotword Set、Provider Config、Episode context。

输出：VADSegment、TranscriptSegment、TokenAlignment、SpeakerObservation、AudioEvent、SpeechQualityReport。

---

## 2. Provider 分层

| 能力 | 首选候选 | 对照/回退 | 说明 |
|---|---|---|---|
| VAD | FunASR/独立 VAD provider | energy rule | 保留 speech probability 与边界 |
| 中文 ASR | FunASR provider | faster-whisper/Whisper | 按方言、BGM、喊叫实测 |
| 标点/文本规范化 | ASR provider 或独立模型 | deterministic rules | 原始文本与规范文本同时保存 |
| Forced Alignment | WhisperX/可替换 aligner | ASR timestamps | 中文字符/词基准单独评价 |
| Diarization | 可替换 diarization provider | speaker embedding clustering | cluster 不命名角色 |
| Audio Event | 规则+合规分类器 | VLM/LLM 不参与原始检测 | 只生成候选观察 |

所有 Provider 实现统一 `capabilities/validate/estimate/infer/health/identity/license` 接口。

---

## 3. 处理流程

```text
Audio Probe
→ Channel Policy / Resample
→ VAD with Context Padding
→ ASR N-best + Raw Response
→ Text Normalization
→ Word/Character Alignment
→ Diarization on Long Context
→ Overlap Resolution
→ Cross-provider Consistency
→ Speech Observation Artifact
```

N-best 只在 Provider 支持时保存；不为统一接口伪造候选。原始文字、规范化文字和人工修正文必须是不同字段或版本。

---

## 4. 时间与边界

- VAD segment 保留前后 context padding，但正式 transcript range 不自动等于 padded range。
- ASR chunk 使用 overlap；合并依据 token 时间、文本相似度和边界质量，禁止简单字符串拼接。
- Diarization 读取长窗口或整集上下文，短 segment 可并发生成 embedding，聚类在汇合点执行。
- 重叠说话允许多个 SpeakerObservation 共享时间范围。
- Alignment 输出 time granularity 和 estimated error，不把近似 timestamp 宣称为帧精确。

---

## 5. 文本与热词治理

Hotword Set 版本化，来源包括角色表、地名、设定词和人工修正。热词只能提升识别候选，不能无证据强制替换同音词。

规范化规则区分：

- 保留语义的标点和数字格式；
- 方言/口语原文；
- 可选展示文本；
- 禁止词或隐私标记。

对话引用默认使用人工批准或最高质量规范文本，同时保留原始识别证据。

---

## 6. Confidence 与冲突

Confidence factors 可包含 acoustic score、对齐稳定性、双模型一致性、SNR、重叠语音和热词影响。模型自报分数未经校准只能处于 shadow。

触发冲突：

- 两 Provider 在关键实体/否定词/数字上不一致；
- token 时间超出 VAD 或源范围；
- speaker cluster 在同一时刻互斥异常；
- 人工修正文与后续自动结果冲突。

冲突进入 Review Package，不由 LLM 猜测消解。

---

## 7. 并发、缓存与降级

- Episode 音轨并行；VAD 后 segment micro-batch。
- 同模型常驻 Worker，按语言、采样率和模型版本分 batch。
- Diarization 聚类、全局 speaker normalization 在 Episode 汇合点执行。
- 云端 ASR 使用并发限额、预算和数据出境 Policy。
- 主 Provider 失败可路由已准入回退 Provider；结果记录 fallback reason，不能伪装为相同模型。
- 模型不可用时输出 unavailable 并允许人工 transcript，不阻塞其他视觉感知。

缓存键包括 audio checksum、channel policy、provider identity、model checksum、decode config 和 hotword version。

---

## 8. 评测与测试

离线数据集按清晰对白、BGM、重叠、方言、喊叫、电话声和角色专名分层。指标至少包括 CER、关键实体错误率、否定词错误率、timestamp deviation、diarization DER/JER 与严重错误率。

工程测试：

- chunk overlap 去重、空音频、多音轨和超长音频；
- Worker kill/heartbeat 恢复与幂等提交；
- 热词版本变化只失效相关 ASR 派生结果；
- 人工修正 transcript 后 Story 依赖精准失效；
- Provider 回退、预算耗尽和数据出境禁止时均显式记录。

