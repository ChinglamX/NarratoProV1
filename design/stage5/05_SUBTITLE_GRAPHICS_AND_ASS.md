# Subtitle, Graphics and ASS

Version: 1.0

## 1. 目标

根据真实 Alignment 和画面布局生成同步、可读、层级清晰、不遮挡关键内容的字幕与包装轨，并通过 ASS/libass 获得可复现服务端渲染。

输入：ConformedTimelineRef、Narration/Dialogue Text、Alignment、CropPath/Saliency/OCR、Subtitle/Graphics/Platform Profile、Font Rights。

输出：SubtitleCueSet、GraphicsCueSet、LayoutPlan、ASS Artifact、CollisionReport、SubtitleQC。

---

## 2. 轨道与来源

- narration subtitle；
- selected original-dialogue subtitle；
- emphasis words/phrases；
- character/location/context cards；
- Hook/Ending/CTA graphics；
- preserved source subtitle region metadata。

不同来源不复制为同一 cue。每个 Cue 记录 source line/alignment、timeline range、text、style、layout、animation intent、evidence/creative refs 和 status。

---

## 3. 断句与时间

断句综合语义、标点、呼吸、字词 Alignment、最大行数/宽度、最短/最长展示和阅读速度 Profile。不得仅按固定字数切断姓名、短语或语义单元。

Cue 时间优先来自真实 Alignment；句级低精度必须标记并扩大人工审核。强调词的动画区间不能早于实际发音造成剧透，也不能晚到失去同步。

字幕与 Voice/Timestamp 修改必须重新生成相关 Cue。

---

## 4. Layout Solver

输入动态禁区：人脸、关键人物/物体、场景文字、原片字幕、平台 UI safe area 和其他 graphics。输出区域、alignment、margin、font size、line breaks 和稳定窗口。

目标顺序：可读性/安全区 → 不挡关键内容 → 位置稳定 → 风格偏好。使用滞后和最短保持时间，防止自动避让上下跳动。

无可行布局时依次尝试缩小到合法下限、重新断句、切换预设区域、背景条/画布扩展或 manual；禁止越界或压到不可读。

---

## 5. ASS 与字体

ASS 保存 style、position、outline/shadow、颜色、layer 和受控动画；libass/FFmpeg 为服务器基线。前端预览必须加载相同字体文件、fallback 顺序和 Profile。

所有字体记录 checksum、license、family/style、fallback 和字符覆盖。缺字或字体权利未知是 Preflight blocker；禁止依赖运行机器上未登记的系统字体。

动画模板必须版本化并限制复杂度，避免不同 libass/build 表现漂移。

---

## 6. Graphics

Character card、地点卡、重点强调和 Ending Card 使用 typed GraphicsCue，不直接保存不可编辑烧录图。模板声明布局槽位、safe area、字体/图片 rights 和动画曲线。

Graphics 内容必须来自 Approved Brief/Story，不新增未经批准身份或营销承诺。

---

## 7. 并发与预览

Cue 初稿可按 Narration Line/Beat 并行；全片布局碰撞、位置稳定和层级检查在汇合点执行。局部修改只重排受影响时间窗口及 handles。

字幕/graphics preview 与 Final 使用同一 ASS/overlay compiler；浏览器近似预览必须显示 parity risk，并以服务端抽帧为验收依据。

---

## 8. 测试与验收

- 长句、数字、人名、双语、标点、快速语速和句级 Alignment。
- 人脸移动、多人、原片字幕、平台 UI、人物卡同时出现。
- safe area、最大行数、阅读速度、缺字和 layout collision。
- 强调词与发音同步、位置抖动和动画越界。
- 不同 FFmpeg/libass build 的 golden-frame comparison。
- 字体权利未知或缺字时无法进入 Final Render。

