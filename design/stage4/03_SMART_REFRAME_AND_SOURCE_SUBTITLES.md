# Smart Reframe and Source Subtitle Handling

Version: 1.0

## 1. 目标

把源素材转换为目标画幅的可执行构图轨迹，同时保护关键人物、动作、物体和原片字幕；自动裁切不可行时提供稳定降级方案。

输入：Selected Clip ranges、Person/Face/Object/OCR tracks、saliency、Platform safe areas、Visual Profile。

输出：CropPath、CompositionReport、SourceSubtitleHandlingPlan、ReframeFallback、VisualPatchProposal。

---

## 2. 工具与执行边界

- OpenCV：几何、光流、轨迹平滑、画面/碰撞分析。
- Stage 2 detection/tracking/identity：主体和关键对象轨迹。
- OCR TextTrack：原片字幕、水印和场景文字区域。
- FFmpeg crop/scale/pad/overlay：preview 与 Stage 5 的确定性执行。
- VLM：主体优先级或语义构图候选，不直接生成不可解释坐标。

CropPath 使用归一化坐标和 RationalTime keyframes，Compiler 转换到具体分辨率。

---

## 3. 主体与构图约束

每个时间窗口构建 composition targets：人物脸/身体、说话人、动作对象、关键场景文字和人工 anchor。目标具有 priority、min coverage、preferred zone、allowed crop 和 confidence。

硬约束：不能切掉关键脸部/动作证据、不能使 Hook 无法理解、不能裁掉必须保留的场景文字、不能违反目标 safe area。

软偏好：三分构图、视线空间、运动前置空间、头顶余量和视觉稳定性。

---

## 4. CropPath 求解

1. 按帧/窗口生成 feasible crop regions。
2. 结合主体优先级和 source subtitle policy 评分。
3. 用平滑/动态规划优化路径，限制速度、加速度和方向抖动。
4. 在 Shot 边界允许重新初始化；Shot 内保持稳定。
5. 对多人分离或互斥目标生成 split-screen/background/pad fallback candidate。
6. 输出路径、违反项和 fallback reason。

自动跟随不能逐帧追脸造成晃动。滞后、死区和最短保持时间由 Visual Profile 配置。

---

## 5. 原片字幕处理

策略枚举：preserve、crop_out、mask/cover、blur、inpaint_candidate、reposition_canvas、manual。

选择依据：字幕是否承载剧情、OCR 可靠性、位置、目标裁切、画面损伤、是否有干净源和后续字幕方案。Stage 4 只生成处理意图；高风险修复需 Stage 5 preview 与人工批准。

禁止默认 inpaint：运动背景、人脸附近和大面积字幕可能产生明显伪影。保留原字幕时必须处理与新增字幕的层级和碰撞。

---

## 6. 降级顺序

配置化候选通常包括：

1. 平滑单一 crop；
2. 人工关键帧补充；
3. 扩大 crop/允许安全留边；
4. blurred/background fill 或 pad；
5. 双人 split layout；
6. 选择替代镜头；
7. 标记 manual composition。

顺序不是全项目硬编码，最终选择记录画质、构图和成本取舍。

---

## 7. 并发与增量

Clip CropPath 并行；单 Clip 内按时间顺序求解。多人/字幕复杂片段可进入高成本队列。序列汇合后检查相邻镜头构图跳变。

人工 keyframe 锁定局部区间；重新生成不得移动锁定点。目标画幅/Profile 变化只失效 Crop/Composition/Preview，不重算 Story 或 Clip relevance。

---

## 8. 测试与验收

- 单人、双人、多人交叉、快速运动、遮挡、镜头摇移和静态宽景。
- 烧录字幕、人脸附近字幕、竖排字、水印和场景关键文字。
- CropPath 速度/加速度/覆盖率和 safe-area 机器检查。
- Preview/Final adapter 对相同 keyframe 产生一致几何结果。
- 不可行构图必须选择 fallback 或 manual，不能输出越界 crop。
- 人工 keyframe 在局部重算后保持不变。

