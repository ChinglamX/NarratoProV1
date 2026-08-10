# Timeline Production Plane Detailed Design

Version: 1.0

## 1. 目标

把 Approved Strategy 编译为专业、可精修、可重复渲染的 Master Timeline，并保证画面、节奏、解说、声音、字幕和包装在统一 timebase 下协同。

---

## 2. 核心技术选择

- 内部 Timeline Schema：项目自有强类型模型，表达 Evidence、依赖、生成参数和失效规则。
- OpenTimelineIO：编辑交换和行业兼容层；映射 Clip、Track、Transition、Marker 和 metadata。
- FFmpeg：代理、滤镜图、音频处理、字幕 burn-in 和最终编码执行器。
- libass/ASS：生产字幕排版与渲染基线。
- OpenCV：画面分析、几何校验、裁切轨迹和质量检测。

OTIO 本身不嵌入媒体，也不是渲染器；不能用 OTIO 替代 Artifact Registry 或 FFmpeg。

---

## 3. Master Timeline 模型

### Track

- video_main
- video_overlay
- original_dialogue
- narration
- bgm
- sfx
- subtitle_primary
- subtitle_emphasis
- overlay_graphics

### Item

- source media reference 与 source range
- timeline range
- transform/crop/keyframes
- gain/ducking/effects
- text/style/layout
- evidence/story/strategy references
- generation dependencies

### 版本与失效

- Timeline 是 immutable artifact。
- Patch 以语义操作表达：trim、move、replace、split、retime、change_text、change_style。
- TTS 时长、镜头边界或转场变化产生新版本。
- 依赖图计算需要重新生成的 Voice/Subtitle/Mix/Render，禁止静默复用过期产物。

---

## 4. Timeline Compiler

输入：Approved Strategy、Hook、Story/Evidence、Media Catalog、Platform Profile、Genre Config。

输出：Timeline Draft 和 Constraint Report。

建设过程：

1. Narrative beat 编排。
2. 每个 beat 检索候选素材。
3. Visual、Rhythm、Narration 三个 planner 并行提出局部计划。
4. Constraint solver 合并时长、证据、连续性和平台约束。
5. Conflict 生成结构化 artifact，交 AI 修复或人工决定。
6. 生成 Timeline Draft。

不使用“最后写入者覆盖”的合并方式。每个 planner 只能产生 Patch Proposal，由 Compiler 统一提交。

---

## 5. Visual Direction

### 能力

- 素材候选排序与连续性
- 9:16 智能重构
- 主体跟随、多人构图和裁切关键帧
- Shot size、运动方向、视线和色彩连续性
- 原片内嵌字幕检测与处理策略
- 人物卡、身份标签和强调包装意图

### 工具

- OpenCV：检测结果几何分析、光流/稳定性、画面检测。
- 人/脸/物 tracking provider：输出主体轨迹。
- FFmpeg crop/scale/pad/overlay：确定性执行。
- VLM：仅为构图和语义候选提供建议。

### 输入输出

输入：Shot/Track/OCR/Quality Features、Story beat、Platform safe area。

输出：Clip Selection、Crop Path、Overlay Intent、Continuity Risk。

### 并发

- 候选 Shot 可并行评分。
- 单 Shot crop path 计算可并行。
- 跨 Shot continuity 必须在序列层检查。

### 局限

多人交互、快速运动、主体交叉和原片构图可能无法自动裁成竖屏；必须支持关键帧人工修正和 letterbox/背景填充降级。

---

## 6. Rhythm Engineering

### 模型

节奏不是单一分数，而是多约束 Timeline：

- beat information load
- emotional intensity
- shot duration
- narration rate
- dialogue preservation
- transition and breathing point

### 建设

1. Strategy 产生目标情绪曲线。
2. Story beat 提供信息和情绪变化。
3. Planner 提议每个 beat 的时长预算。
4. Timeline Compiler 在目标总时长内优化。
5. 规则检测过密、过慢、机械快切和高潮堆叠。
6. 人工可拖动 beat、镜头和停顿，系统局部 reflow。

### 输入输出

输入：Narrative beats、候选 Shot、Dialogue/Narration estimated duration、Genre preferences。

输出：Beat Budget、Shot Duration Proposal、Transition、Rhythm Curve、Risk。

### AI 自动化与局限

AI 可生成候选曲线、识别明显拖沓/过密并提出多版本。它不能可靠决定“差 0.5 秒的艺术感”；最终节奏必须以 benchmark、人工听看和线上数据校准。

---

## 7. Narration Engineering

### 生产链

```text
Narration Outline
→ Evidence-constrained Draft
→ Spoken-language Rewrite
→ Redundancy / Fact Check
→ Emotion / Pace / Pause Annotation
→ TTS Candidate
→ Forced Alignment
→ Timeline Reflow
```

### 输入

Approved Strategy、Story/Evidence、selected clips、beat budget、Genre Narration Profile。

### 输出

Narration Line：text、intent、evidence、target duration、emotion、pace、pause、pronunciation hints。

### 建设

- LangGraph 分节点生成和审核，不用单 Prompt 同时完成剧情、文风和时长控制。
- Fact checker 只允许证据支持或明确标注的表达性修辞。
- 与原对白做语义重复检查。
- 目标字数由真实 TTS provider 的历史语速模型估算。
- 每个重要人名、地名和多音字进入 pronunciation dictionary。

### 并发

- 不同 beat 初稿可并行。
- 全文语体、指代和递进需要全局 pass。
- 多风格版本可并行，但限制候选数量。

### 局限

模型容易书面化、过度解释、虚构心理活动和一步到位地放大情绪。必须保留逐句 Evidence、人工润色和版本对比。

---

## 8. TTS & Alignment

### Provider 选择

- IndexTTS2：候选，用于中文情感与时长控制场景；生产前核对模型许可、可用功能和稳定性。
- CosyVoice：候选，用于多语言、方言、情感/速度指令和流式能力。
- 商业 TTS：作为质量/稳定性基准和降级 provider。

不把任何单一 TTS 写入业务契约。Provider 必须实现：synthesize、health、capabilities、estimate_cost、rights_metadata。

### 流程

1. 文本规范化和发音词典。
2. 按句/语义段生成候选。
3. 音频技术检测：静音、削波、采样率、时长。
4. ASR back-check：检测漏字、错音和重复。
5. Forced alignment 得到实际时间。
6. 写回 Timeline；超出预算时优先重写文本或调整停顿，不盲目极端拉伸。

### 并发

- 独立句段可并行生成。
- 同一 voice/model 使用受控 batch，避免显存/统一内存爆炸。
- 合成后全局 loudness、音色和韵律一致性检查。

### 局限

克隆音色、情感和时长控制互相影响；“精确时长”不代表自然。音色必须具有授权，禁止无授权克隆演员声音。

---

## 9. Audio Design

### 工具

- FFmpeg filtergraph：amix、sidechaincompress、loudnorm、limiter、fade、EQ 等。
- EBU R128/ITU-R BS.1770 思路用于可重复响度测量；最终平台目标由 Platform Profile 定义，不机械套用广播 -23 LUFS。
- 音频特征/检索模型：BGM 候选检索，不直接决定使用权利。

### 轨道

- original dialogue/ambience
- narration
- bgm
- sfx/accent

### 建设

- 先形成 Mix Plan，再编译为 FFmpeg graph。
- narration 是主可懂度目标；原对白按剧情需要保留。
- Ducking 使用时间包络，不仅设置一个固定音量。
- BGM 选择同时考虑情绪、结构、节拍、长度、循环点和许可证。
- 输出测量 Integrated/Short-term Loudness、True Peak、clipping 和 silence。

### 并发

BGM/SFX 检索与 TTS 可并行；最终混音必须在 Timeline conform 后执行。

---

## 10. Subtitle & Graphics

### 工具

- ASS 作为生产字幕描述格式。
- libass/FFmpeg 作为服务器渲染基线。
- 前端预览必须与服务端字体、字号、描边和 safe area 使用同一配置。

### 能力

- 语义断句与最大行宽
- narration/原片/强调字幕多轨
- 重点词高亮
- 人物卡、地点卡、Ending Card
- 人脸/OCR/关键物体避让
- 动画模板与时间曲线

### 输入输出

输入：Alignment、Text、Visual Saliency、Platform Profile、Style Config。

输出：Subtitle/Overlay Timeline、ASS、Layout Collision Report。

### 并发

Cue 生成可并行，最终布局需按时间窗口检查多元素碰撞。

### 局限

自动避让可能频繁跳动；应使用滞后和区域稳定策略。原片硬字幕修复可能损伤画面，必须允许保留、遮罩、裁切、模糊或人工选择。

---

## 11. Rendering

### Render Graph

Timeline Compiler 将媒体引用和参数编译为 deterministic Render Plan，再生成 FFmpeg command/filtergraph。

步骤：

1. Preflight：资产、字体、时长、rights、磁盘。
2. Proxy Preview：低分辨率快速审核。
3. Final Render：目标规格。
4. Technical QC：ffprobe、黑帧、静音、时长、响度、字幕抽帧。
5. 原子注册 Render Artifact。

### 并发

- Variant 可并行渲染。
- 同一机器并发由编码器、内存、磁盘和热限制决定。
- 共享中间片段用 checksum cache。
- 不把一个 FFmpeg 进程内部 filter threading 当作无限外部并发依据。

### 效果

- Preview 与 Final 使用同一 Timeline 和 filter compiler。
- 渲染命令、工具版本、字体、平台配置完整记录。
- 相同输入和确定性参数产生可复现结果。

---

## 12. Review Workspace

必须提供：

- 多轨 Timeline 预览
- Story Evidence 跳转
- Hook/Strategy 对比
- 镜头 trim/reorder/replace
- Crop keyframe 调整
- Narration 文本、情感、停顿和发音调整
- BGM/SFX/gain/ducking 调整
- Subtitle 文本、断句、位置和样式调整
- 版本差异和局部重新生成

前端可使用 TypeScript/React 实现，但核心计算仍在 Python/FFmpeg Worker；“不大量使用 Node.js 作为核心计算层”不等于禁止专业 Web UI。

---

## 13. 生产验收

- Timeline round-trip 到 OTIO 后关键编辑信息不丢失；项目私有 metadata 有版本。
- 所有轨道统一 timebase，无静默漂移。
- TTS 改动正确失效 Alignment、Subtitle、Mix 和 Render。
- Preview/Final 构图一致。
- 字幕不越界且关键画面碰撞可定位。
- Audio 技术指标可机器验证。
- demo benchmark 的视觉、节奏、解说、音频、字幕逐项达到配置阈值。
