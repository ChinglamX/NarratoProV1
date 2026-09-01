# D5 标注指南（给项目负责人）

目标：为 24 帧标注**参考答案**，用于计算 OCR 准确率（CER）、人物/物体识别准确率（mAP 代理）、VLM 描述合规率。

## 你需要做的一共 3 步

### 第 1 步：打开帧图片
- 打开文件夹 `evaluation/evidence/d5_annotation_kit/frames/`
- 里面 24 张 jpg，文件名格式：`系列_集数_第几帧_时间点.jpg`（如 `e06-1982_e01_f01_07.02s.jpg` = 系列 e06-1982 第 1 集第 1 帧，源视频 7.02 秒处）
- 双击用「预览」查看，和下面的工作表一一对应

### 第 2 步：打开工作表
`evaluation/evidence/d5_annotation_kit/annotation_worksheet.json`
每帧有 3 个**空栏**要填（机器预填 `machine_prefill` 只作参考，别照抄——它可能有错）：

| 空栏 | 填什么 | 示例 |
|---|---|---|
| `ocr_reference_text` | 画面里**逐字可见的文字**（字幕/招牌/证件）；没有就留空 | `别赶我走好不好` |
| `det_reference_boxes` | 画面里的**人物/关键物体**（几个、在哪）；没有就写 `无` | `2人：女子左下、男子右下` |
| `vlm_claim_verdict` | 一句话：画面与剧情**相关吗**（related/not）+ 机器描述**有没有编造**（hallucinated yes/no） | `related, hallucinated no` |

### 第 3 步：填完保存，然后告诉我
填好后**直接告诉我一声**（或把 json 发我），我运行指标计算器出第一集结果。

---

## 第 1 帧完整填法示例（e06-1982_e01_f01_07.02s.jpg）

画面内容（机器预填，供你核对）：夜晚简陋小屋内，穿粉色碎花睡衣的女子神情凄然恳求地看向身旁闭眼男子，画面下方配文「别赶我走 好不好」。

```json
{
  "series": "e06-1982",
  "episode": "e01",
  "frame": "e06-1982_e01_f01_07.02s.jpg",
  "ocr_reference_text": "别赶我走好不好",
  "det_reference_boxes": "2人：女子左侧恳求、男子右侧闭眼",
  "vlm_claim_verdict": "related, hallucinated no"
}
```

### 填写的三条心法
1. **OCR 栏**：只写画面里真正出现的字，错一个字都算错误（CER 会扣分）。
2. **DET 栏**：数清楚人物/关键物体。写「人」「卡」「车」「钱」等词即可（识别器支持中英文）。
3. **VLM 栏**：先看机器描述（`machine_prefill.vlm_description`），再对照画面——描述基本准确就 `related, hallucinated no`；如果机器编了画面里没有的东西（如说「窗外有雪」但实际没有）就 `hallucinated yes`；画面与剧情无关就 `not`。

---

## 偷懒方案（推荐）
不想手改 JSON 的话，直接在聊天里把标注发给我，格式随意，例如：

> 「f01：字幕=别赶我走好不好；画面=2人（女子左、男子右）；VLM=related 无误」
> 「f02：无字幕；画面=1人；VLM=related 无误」
> ……

我负责转成 JSON 并跑指标。**先标 e06-1982/e01 的 8 帧（约 15 分钟）试流程**即可，确认没问题再标其余 2 集。
