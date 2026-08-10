# M9.1 FigureSpec 验收

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m9-figures`

## 验收范围

本批次验证 FigureSpec 输入点、输出格式、相对数据/脚本路径、内容 SHA-256、0017 迁移回滚，以及只允许 verified/final MetricResult 和一致 data_version 的 Repository 门禁。尚未生成图像文件。

## 命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_m9_figure_repository.py` | 通过，3 passed |
| `uv run python scripts/check.py` | 通过，146 passed；Fixture 校验通过 |
| `uv run ruff format --check src tests scripts` | 通过，111 files formatted/unchanged |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `git diff --check` | 通过 |

## 限制

M9.1 没有声称 PNG/SVG/PDF 已生成，也没有进行视觉验收；输入指标来自合成/脱敏 Run。M9.2–M9.4 必须继续验证删除图后可由同一数据和脚本重建，且图中数字与 MetricResult 一致。
