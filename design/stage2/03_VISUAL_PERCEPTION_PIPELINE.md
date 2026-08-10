# Visual Perception Pipeline

Version: 1.0

## 1. 目标

对版本化 FrameSamplePlan 和短片段执行 OCR、人物/物体检测、Shot 内跟踪、人物外观特征、Embedding 与受约束 VLM 描述，生成独立 Observation；本模块不直接形成剧情结论。

输入：Shot、FrameSamplePlan、Analysis Proxy、Provider Config、Visual Prompt Set。

输出：OCRObservation、DetectionObservation、Tracklet、FaceObservation、VisualEmbedding、VLMObservation、VisualQualityReport。

---

## 2. 能力与工具边界

| 能力 | 候选工具 | 生产建设方式 | 不能直接证明 |
|---|---|---|---|
| OCR | PaddleOCR | 检测、方向、识别、跨帧文字轨迹分离 | 文字属于谁、内容一定真实 |
| 固定类检测 | 经许可审核的 detector | 人、常见物体；版本化 label map | 开放世界实体身份 |
| 开放词汇检测 | Grounding DINO | prompt set 版本化，只作候选 | “妖怪”等剧情设定为真 |
| Tracking | ByteTrack 类 provider | Shot 内按帧顺序处理 | 跨 Shot 是同一人物 |
| Face/Appearance | 合规 embedding provider | 项目内临时身份特征 | 法律意义身份或演员姓名 |
| Embedding | CLIP/SigLIP 类 | Shot/区域检索，索引绑定模型版本 | 相似即同一事件 |
| VLM | bake-off 选定 provider | typed schema、限定证据帧、短片段 | 稳定理解长时序与隐含动机 |

代码许可证与权重许可证分别登记。InsightFace 官方预训练权重不能未经授权成为商业默认模型；检测器也必须核对实际代码和权重条款。

---

## 3. OCR 设计

OCR 输出必须区分：

- burned_in_subtitle：原片字幕；
- scene_text：标牌、信件、手机和文件；
- graphic_overlay：片头、角标、水印和平台 UI；
- unknown。

跨帧聚合使用文本相似度、空间 IoU、运动一致性和时间连续性。相同字幕连续出现只形成一个 TextTrack，保留所有帧级 observation 作为证据。

OCR 不得依据 ASR 自动改写原观察；ASR/OCR 一致性在 Fusion 层生成新的 cross-modal evidence。

---

## 4. Detection、Tracking 与人物观察

1. Frame detector 产生 bbox/mask/landmark candidate。
2. Shot 内 tracker 顺序处理，生成 Tracklet。
3. 选择清晰、正侧脸、多尺度的代表 crop。
4. 提取 face/appearance embedding 和质量特征。
5. 跨 Shot 关联交给 Identity Fusion，不在 tracker 内偷偷合并。

Tracklet 记录 frame-range、检测覆盖率、遮挡、代表图、provider 和 uncertainty。换镜头后即使外观相似也只能产生 link candidate。

---

## 5. VLM 使用协议

VLM 只读取明确的帧/短片段和结构化问题，例如可见人物、动作候选、物体关系、场景变化。输出必须：

- 引用具体 frame/time range；
- 区分 visible、inferred、unknown；
- 不输出未要求的完整剧情续写；
- 保存 prompt、sampling、model identity 和 raw response；
- Schema 校验失败时重试修复有限次数，之后标记 unavailable。

“愤怒”“想报复”等不能成为 Fact；可记录皱眉、握拳、提高音量等可观察信号，语义解释进入 Story 层。

---

## 6. 采样与主动补采

第一轮使用用途特定 FrameSamplePlan。若产生以下信号，可生成 SupplementarySampleRequest：

- 人脸质量不足但身份重要；
- OCR 文字轨迹首尾不完整；
- Shot 内动作在稀疏帧间不连续；
- VLM 结论只由单帧支持；
- Provider 之间冲突。

补采有每 Shot/Project 预算，不能无限递归。请求必须记录触发原因和预期消除的不确定性。

---

## 7. 并发与资源

- Shot/Frame batch 并行，单个 Track 计算保持时间顺序。
- OCR、detector、embedding、VLM 使用独立 Task Queue 和显存 semaphore。
- 同模型按输入尺寸分桶 micro-batch，避免 padding 浪费。
- VLM 先由便宜的候选筛选器控制调用范围；不得对所有帧无差别调用。
- 大 crop、frame 和 raw response 写 Object Store；数据库只保存索引和摘要。
- Worker OOM 降低 batch 后有限重试；重复 OOM 隔离输入并记录 resource failure。

---

## 8. 测试与验收

- 烧录字幕、竖排字、手机屏、运动模糊、遮挡和水印数据集分别评测。
- 人群、侧脸、换装、夜景、快速运动和跨镜转场样本覆盖。
- Shot 分块不破坏 Tracklet，人工 Shot 修正触发正确重算。
- VLM 不可见信息测试和诱导幻觉测试进入 benchmark。
- Embedding model 更换创建新索引，不能混用向量空间。
- 权重缺少商用授权时 Provider 无法进入 production policy。

