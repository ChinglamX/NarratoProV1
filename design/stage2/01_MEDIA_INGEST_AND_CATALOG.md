# Media Ingest and Catalog

Version: 1.0

## 1. 目标与边界

建立原始资产身份、技术属性、统一时间坐标和可重复使用的代理素材。该模块只描述媒体结构，不解释剧情。

输入：Source Asset ArtifactRef、Rights Metadata、Episode Manifest、Media Profile。

输出：MediaAsset、MediaProbe、Episode、ProxyAsset、AudioStem、SceneCandidate、Shot、FrameSamplePlan、QualityFeature。

---

## 2. 开源工具

| 工具 | 用途 | 边界 |
|---|---|---|
| FFprobe | stream、codec、duration、timebase、rotation、color、audio layout | 输出需映射到内部 Schema，不能直接散落 JSON 字段 |
| FFmpeg | remux、proxy、audio demux、thumbnail、质量测量 | 命令与 build/config 必须记录 |
| PySceneDetect | Content/Adaptive/Threshold 基线 | 产生 cut candidate，不是真相 |
| TransNetV2 候选 | 神经网络转场对照 | 只有许可证与项目 benchmark 通过后启用 |
| OpenCV | 黑帧、冻结、模糊、亮度和采样验证 | 不承担最终编解码 |

---

## 3. Ingest 协议

1. 验证 URI、权限、大小、MIME 和可读取性。
2. 流式计算 SHA-256；相同 blob 复用，项目引用独立保留。
3. FFprobe 生成原始响应 artifact，再规范化为 MediaProbe。
4. 校验 duration、stream start、VFR、rotation、edit list、音视频缺失和损坏。
5. 写入 Rights Snapshot；权利未知可进入理解流程，但必须阻断 Release。
6. 原子提交 Source Asset 与 catalog version。

幂等键：`source_checksum + ingest_profile_version`。文件名、路径和上传时间不能作为资产身份。

失败：损坏、加密或不支持媒体标记 `unreadable/unsupported`；禁止生成伪造时长。可恢复网络读取按 Range/分片续传。

---

## 4. 时间坐标

- 源坐标使用 RationalTime，保存 stream time_base、start_time 和原始 PTS/DTS 特征。
- 所有代理建立 `source_to_proxy_time_map`；CFR 代理不能抹掉 VFR 源映射。
- 音频重采样保留 sample-rate 转换参数和首尾 padding。
- rotation 作为显示变换保存；分析帧注明在 encoded space 或 display space。
- Episode order 是版本化关系，不拼接成不可逆的大文件。

每个下游 EvidenceLink 必须能转换回 `source_asset_id + source_range`。

---

## 5. Proxy 与派生素材

Profile 由配置定义：codec、分辨率、帧率策略、色彩、音频采样率和质量。默认产生：

- review proxy：可快速拖动和浏览；
- analysis proxy：适合解码和抽帧，不用于最终渲染；
- mono speech stem：ASR 输入；
- optional waveform/thumbnail：UI 和定位。

代理只是缓存型 Artifact。Profile 或 FFmpeg build 变化只失效代理及依赖它的数值结果，不失效 Source Asset。

---

## 6. Scene、Shot 与采样

Detector 输出 `boundary_candidate(time, score, detector)`。融合器按时间容差聚类，再由规则处理：

- 最短 Shot、闪光和黑场候选；
- 渐变/叠化区间而非单点 cut；
- 分块边界使用重叠窗口；
- 人工 split/merge 生成 corrected Shot version。

FrameSamplePlan 按用途独立版本化：OCR 需要文字变化敏感采样，Identity 需要清晰人脸采样，VLM 需要关键帧与短片段。禁止用固定“每 N 秒一帧”满足所有任务。

---

## 7. Source Quality Features

确定性特征包括黑帧、冻结、模糊、过曝/欠曝、画面尺寸、音频削波、静音和响度区间。学习型审美或表演信号必须标为候选，不作为硬删除条件。

输出包含 metric、window、method、threshold profile 和 raw value。Strategy/Timeline 决定是否选用素材，Intelligence 始终保留其剧情证据。

---

## 8. 并发与资源

- 不同 Episode 并行；同一资产 probe/checksum 只执行一次。
- FFmpeg 转码按磁盘带宽、硬件编码器 session 和 CPU admission 控制。
- Shot detection 可分块，块间至少保留配置化 overlap 并统一去重。
- thumbnail/frame extraction 合并为少量 FFmpeg pass，避免每帧启动进程。
- 磁盘临时空间不足时 fail before start，不边写边 OOM/ENOSPC。

---

## 9. 测试与验收

- CFR、VFR、旋转、非零 start time、缺音轨、多音轨和损坏样本。
- Source↔Proxy 时间映射 round-trip 误差符合 Media Profile。
- 同一 checksum 重复 ingest 不产生重复正式 blob。
- 分块与整段 shot detection 的边界结果可解释并在容差内一致。
- 人工 split/merge 可恢复上一版本并精准失效 FrameSamplePlan。
- Worker 中断后不会留下被引用的半成品代理。

