# M9 图表视觉验收

日期：2026-08-11（Asia/Shanghai）

## 验收对象

验收对象是 M9 集成测试生成的合成/脱敏农业视觉图表 Bundle：

`.pytest-tmp/test_figure_caption_suggestion0/artifacts/figure-m9/`

Bundle 中的 `figure.png`、`figure.svg` 和 `figure.pdf` 来自同一份 `FigureSpec`、`input-data.csv` 和 `generate_figure.py`。输入指标为脱敏 Fixture 数据，不是真实农业试验结果。

## 实际检查

1. `figure.png` 使用本地图像查看器打开。
2. `figure.svg` 使用 Chrome headless 加载并截图到 `.verification/m9-visual-qa-20260811/figure-svg-render.png`，再打开截图检查。
3. `figure.pdf` 使用 Poppler `pdftoppm` 渲染到 `.verification/m9-visual-qa-20260811/figure-pdf-1.png`，再打开渲染结果检查。

三种输出均检查了画布边界、标题、坐标轴、刻度、图例/类别标签和数据区域。实际结果：未发现裁切、重叠、黑块或不可读标签；SVG 与 PDF 渲染结果的布局与 PNG 一致。

## 可复现性与边界

`uv run python scripts/check.py` 通过了图表 Bundle 的删除后脚本重建、数值一致性和 provenance hash 检查。视觉检查证明的是当前合成/脱敏输入下的输出可读性，不证明真实农业数据、论文结论、统计显著性或部署质量。真实数据进入正式科研产物前仍需独立数据与人工审查。
