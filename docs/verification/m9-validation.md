# M9.3 图表建议与数值一致性验收

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m9-figures`

## 验收范围

本批次验证 verified-only 图表建议、来源型 Caption、CSV 与 MetricResult 数值一致性、data/script hash 和 provenance 字段检查。视觉质量仍需 M9.4 实际打开图像验收。

## 命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_m9_figure_repository.py` | 通过，6 passed |
| `uv run python scripts/check.py` | 通过，149 passed；Fixture 校验通过 |
| `uv run ruff format --check src tests scripts` | 通过，114 files formatted/unchanged |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `git diff --check` | 通过 |

## 限制

测试使用合成/脱敏 MetricResult 和本地 Bundle；数值链通过不代表图形布局、可读性或真实科研图表已经视觉验收。M9.4 必须实际打开 PNG/SVG/PDF 并保存验收证据。
