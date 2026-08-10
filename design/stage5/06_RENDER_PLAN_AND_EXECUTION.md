# Render Plan and Execution

Version: 1.0

## 1. 目标

把 Conformed Timeline、Mixed Audio、ASS/Graphics 和平台规格编译为确定性 RenderPlan，可靠生成 Proxy 和 Final Candidate，并保留完整命令、环境、缓存与失败信息。

输入：ConformedTimelineRef、Media/Voice/MixedAudio/ASS/Graphics refs、Platform/Render Profile、Rights Preflight。

输出：RenderPlan、FFmpeg Command/Filtergraph Artifact、ProxyRender、FinalCandidate、RenderExecutionReport。

---

## 2. RenderPlan

包含：

- 精确输入 ArtifactRef/checksum/stream selection；
- clip trim/retime、crop/scale/pad、transition/effect；
- overlay/ASS/graphics layers 与字体；
- MixedAudio mapping 与 sync offset；
- color/pixel/aspect/frame-rate policy；
- codec、profile、bitrate/quality、GOP、audio codec；
- expected duration/frames、output path、temporary space；
- FFmpeg build/container/hardware acceleration；
- deterministic/non-deterministic capability declaration。

Command 是 RenderPlan 的编译产物，必须经过 shell-safe 参数数组执行，不拼接未经验证的字符串。

---

## 3. Preflight

渲染前验证全部引用存在且 checksum 正确、rights resolved、字体完整、Timeline/Alignment/Mix/ASS versions 一致、磁盘充足、codec/filter 可用、目标规格完整。

Preflight 失败属于 non-retryable business/config error，禁止启动昂贵 FFmpeg 后才发现缺资产。

---

## 4. 编译与中间产物

复杂 Timeline 可分为 conform segment → shared intermediate → final assembly，但每段必须由 segment checksum 标识。缓存键包含所有输入、transform/effect、compiler/FFmpeg build 和 Profile。

中间编码质量/色彩必须满足无可见累积损伤；是否使用 mezzanine 或直接 filtergraph 由 benchmark 决定，不固定为单一方案。

Proxy 与 Final 共享时间、几何、字幕和音频图语义，只改变明确列出的质量参数。

---

## 5. 执行与恢复

FFmpeg Activity 使用 timeout、heartbeat/progress、stderr structured capture 和取消处理。输出先写 staging，probe/QC 通过后原子注册。

任务中断后：可复用已验证 immutable segments；未完成单文件输出重启，不把损坏 partial 当缓存。重试使用相同 idempotency key。

硬件编码失败可按批准的 fallback profile 切软件编码；新结果记录 fallback，不伪装为相同执行环境。

---

## 6. 并发与资源

不同 Variant/Segment 可并行，但由 CPU、RAM、GPU/VideoToolbox session、磁盘读写/临时空间和热水位 admission 控制。

FFmpeg 内部线程数计入总 CPU 配额。交互 Proxy 和 Final Render 使用独立优先级队列，防止预览饿死正式任务或反向阻塞编辑。

单机容量通过实测确定；不把“能启动多个进程”等同于安全并发。

---

## 7. 安全与可追踪

- 输入路径/URL 通过 Artifact Store 解析和 allowlist，不接受任意协议。
- filter/template 参数类型化并转义。
- 日志不泄露签名 URL、密钥或完整敏感 Prompt。
- command、stderr、progress、资源、duration、exit code 和 tool version 关联 trace/run/artifact。

---

## 8. 测试与验收

- 多 codec、VFR/CFR、旋转、色彩、无音轨/多音轨和长时间线。
- FFmpeg crash、cancel、磁盘满、硬件编码失败和 stale cache。
- 相同 RenderPlan 的结构/时长/帧数可复现；编码字节级确定性按 codec 能力如实声明。
- Proxy/Final 时间、crop、subtitle 和 audio graph parity。
- partial output 不注册，重试不产生重复 Final Candidate。
- 命令注入、任意协议和未登记字体/资产被 Preflight 阻断。

