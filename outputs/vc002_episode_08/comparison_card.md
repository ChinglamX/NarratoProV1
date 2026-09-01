# VC-002 Episode 8 Story Brief 对比卡

## 系统 Story Brief

1. 对白表明有人以三十万购买两样货物，并完成交易。
2. 交易方交出一张内有三十万、密码为六个八的卡。
3. 另一方得知那小子一天得到三十万，因其有钱不还并曾动手，决定盯住并威胁杀死他。

未决问题：

- 仅凭本段研究 ASR 无法可靠确认交易双方姓名及两样货物的具体名称。
- 单段 ASR 没有说话人分离，威胁者与虎哥是否为同一人需要画面或人工确认。

Confidence：`unavailable`；必须 L1 人工审核。

## 人工参考草稿

主角带着两样货物成交三十万并拿到银行卡；虎哥一方得知他有钱后，因欠债和此前冲突派人盯住，准备再次下手。

状态：`producer_draft_pending_human_review`，不能视为已批准人工真值。

## 必要人工判断

1. 系统摘要是否存在关键事实错误？
2. 是否漏掉决定 Hook 的主要冲突？
3. 是否足以支持后续营销方向选择？

Decision：`useful_with_revision`

人工验收（2026-08-19，项目负责人）：系统列出的三条事实信息均正确。当前卡片仍缺少原片播放器、逐条独立时间码和说话人分离，因此只批准 Episode 8 的事实摘要，不外推到自动角色识别、完整 Story Understanding 或下游 Strategy。

## 原片与逐条证据

完整证据段（00:00.520–00:51.025）：

![Episode 8 原片证据段](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/source_review_00m00s520_00m51s025.mp4)

### Claim 1 — 三十万购买两样货物（已重新精确截取）

- 独立审核窗口：原片 `00:15.000–00:28.000`
- 画面说话人：黑衣女性面向摊主/男主报价；只记录视觉角色，不创建 CharacterIdentity。

![Claim 1 原片](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/claim_01_sale_15s_28s.mp4)

![16 秒：三十万](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/16s.jpg)

![17 秒：这两样我都要了](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/17s.jpg)

### Claim 2 — 银行卡金额和密码（已按人工反馈纠正）

- 独立审核窗口：原片 `00:28.000–00:33.000`
- 画面说话人：黑衣女性持卡说明金额和密码，随后将卡递给浅色外套男性。

![Claim 2 原片](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/claim_02_payment_28s_33s.mp4)

![29 秒：卡里有三十万](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/29s.jpg)

![30 秒：密码六个八](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/30s.jpg)

### Claim 3 — 得知钱款并下令盯梢（已重新精确截取）

- 独立审核窗口：原片 `00:39.000–00:53.056`
- 说话人证据：光头男性进屋称呼“虎哥”；皮衣男性随后谈及三十万、不还钱、此前动手并下令盯住。

![Claim 3 原片](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/claim_03_threat_39s_53s056.mp4)

![40 秒：称呼虎哥](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/40s.jpg)

![42 秒：一天得到三十万](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/42s.jpg)

![45 秒：有钱不还](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/45s.jpg)

![48 秒：下令盯住](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/48s.jpg)

![50 秒：威胁弄死](/Users/chinglam/workspace/NarratoProV1/outputs/vc002_episode_08/evidence_frames/50s.jpg)

时间码来自一秒采样、烧录字幕和原声复核，是独立 Claim 审核窗口，不冒充词级强制对齐。说话人证据只证明画面角色关系，尚未建立 canonical CharacterIdentity。

纠正记录：首版片段使用 FFmpeg 输入侧快速 seek，实际落到后续 GOP/关键帧，导致 Claim 2 文件名写 `34–39s`、内容却是通风报信。项目负责人指出后，当前三个片段全部改为输出侧精确 seek 重建，旧错误片段与关键帧已删除。

纠正后复核（2026-08-19，项目负责人）：Claim 2 银行卡金额和密码片段正确。
