# M5.3 设计质量、泄漏与版本比较验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m5-pipeline-data-design`
- 环境：Windows，CPython 3.12.13，SQLite，Pydantic 2
- 数据性质：合成/脱敏农业视觉方案，不是真实数据质量或现场证据

## 已执行命令

```text
uv run pytest tests/integration/test_m5_design_validation.py -q
4 passed

uv run ruff format --check src tests scripts
69 files already formatted

uv run ruff check src tests scripts
All checks passed!

uv run python scripts/check.py
pytest: 109 passed in 44.22s
Fixture validation: 3 synthetic project fixtures passed
```

## 覆盖范围

- 黄金样例的管线连接和分组/来源泄漏控制通过；
- 断开阶段、随机行切分和缺少泄漏控制产生 blocking finding；
- PipelineSpec 版本比较报告 changed fields、added stage IDs 和 removed stage IDs；
- 无效设计调用 `approve_design_pair()` 时保持两个 draft，不写批准状态。

## 限制

当前检查是确定性的结构/关键词门禁，不读取真实图像、CSV 或标注样本，也不判断采样伦理、统计代表性或授权真实性。M5.4 仍需 Markdown/YAML 导出、发布候选和独立环境验收。
