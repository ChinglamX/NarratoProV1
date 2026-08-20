# D5 第一集试标报告（e06-1982/e01，8 帧，owner 标注）

Date: 2026-08-19（State v116）
标注：project-owner（8 帧）；机器预填：PaddleOCR / RT-DETR / Ark VLM（research）
指标：`scripts/accept_d5_metrics.py` → `metrics_report.json`

## 结果

| 指标 | 值 | 说明 |
|---|---|---|
| **OCR 文本帧 CER** | **0.000**（5/5 帧零错误） | 标点/空格/全半角括号归一化后，5 个有字幕帧全部识别正确（含 f03 角色标签「赵海霞/陈云小姨子/卖给家暴男李二狗」） |
| **OCR 误报** | 1 帧（f08「F」） | f08 画面无文字、机器输出「F」——计入 CER（该帧计 1.0），**平均 CER=0.1667** |
| **DET label 级 precision/recall** | **0.8 / 1.0**（修复后） | 原 0/0 为 adapter 解析 bug（标签在 `boxes[].label` 未读取），已修复；person 检出正常，1 误报（f02「toilet」=陶缸被 COCO 误判） |
| **VLM claim 合规率** | **1.0**（8/8） | owner 判定全部 related 且无幻觉 |

## owner 三项发现的处置
1. **f08 误识别**：确认并计入（false positive，CER 贡献 1.0）✅
2. **f03 漏识别疑点**：核实为**未漏**——机器已识别「赵海霞/陈云小姨子/卖给家暴男李二狗」，仅标点差异（、vs 空格），归一化后 CER=0 ✅
3. **f01 空格差异**：CER 函数与归一化已去空格，CER=0 ✅

## 结论与下一步
- 试标流程可行（8 帧约 15 分钟，标注质量高）；**OCR 与 VLM 在试标集表现优秀**。
- **DET 修复后可用**（person recall 1.0）；剩余短板：卡/钱等短剧类别不在 COCO（D6 自定义类别），但不再阻塞 person 级使用。
- 建议：扩展到剩余 2 集（e06-series-07/hot、e06-series-12/e01）16 帧；同步推进 D6 类别体系决策。
