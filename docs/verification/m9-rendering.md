# M9.2 图表渲染验收

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m9-figures`

## 验收范围

本批次验证 approved FigureSpec 的 Artifact Bundle、确定性 CSV、可重建脚本、PNG/SVG/PDF、Caption 和 provenance 文件；删除输出文件后从同一 bundle 脚本重建。数值一致性和人工视觉验收属于 M9.3/M9.4。

## 命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_m9_figure_repository.py` | 通过，5 passed |
| `uv run python scripts/check.py` | 通过，148 passed；Fixture 校验通过 |
| `uv run ruff format --check src tests scripts` | 通过，113 files formatted/unchanged |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `git diff --check` | 通过 |

## 限制

当前输入为合成/脱敏验证指标；测试验证文件存在、非空和脚本重建，不等于视觉审美或真实农业视觉图表验收。M9.3 必须校验图表数字回到 MetricResult，M9.4 必须实际打开图像做视觉检查。
