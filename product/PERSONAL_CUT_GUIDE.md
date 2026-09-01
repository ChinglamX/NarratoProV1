# 个人候选片入口（验证版）

当前入口适用于：素材已经完成内部使用权确认，剧情 Gate 1 与策略 Gate 2 已人工批准。单份配置可包含一个或多个源视频；入口会分别导入每个素材、生成配音/字幕/候选片，再以逐镜头 exact SourceMedia ref 进入 canonical Render/QC，不再绑定某个样片 profile。

它不会自动判断剧情，也不会执行公开发布。

## 只检查，不生成

```bash
make personal-cut-check
```

终端会依次显示：权利与人工 Gate、素材导入、可查看部件、运行环境、canonical 渲染/QC、人工发布边界。

## 执行或断点续跑

```bash
make personal-cut
```

已经完成的 canonical 输出不会重复生成；缺少前置输入时会在对应阶段停止，并用中文说明原因。状态保存在候选目录的 `personal_cut_status.json`。

第 7–8 集已用同一入口完成断点检查：两个 ingest、七段可查看部件、canonical Render/QC 均显示“通过”，Gate 3 单独显示“未执行”。

## 产品边界

- 当前是 M5 操作验证入口，不是任意新素材的一键自动创作入口。
- 修改剧情、营销方向、镜头或解说后，必须重新经过对应人工检查点。
- 输出仅限 `internal-preview`；Gate 3 未执行，禁止公开发布。
