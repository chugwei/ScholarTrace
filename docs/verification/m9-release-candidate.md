# M9 `v0.9.0` 发布候选审查

日期：2026-08-11（Asia/Shanghai）

## 范围

候选版本为 `v0.9.0`，包含 M9.1–M9.4 的 FigureSpec、可重建图表 Bundle、来源型 Caption、数值/provenance 校验和视觉验收。候选使用合成/脱敏农业视觉指标，不能被解释为真实科研结果。

## 验收命令与结果

| 检查 | 结果 |
|---|---|
| `uv run ruff format --check src tests scripts` | 通过，114 files already formatted |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `uv run python scripts/check.py` | 通过，149 passed；3 个合成 Fixture |
| `uv build` | 通过，生成 `scholartrace-0.9.0.tar.gz` 和 `scholartrace-0.9.0-py3-none-any.whl` |
| 独立 venv 安装 wheel、import、CLI | 通过，版本 `0.9.0`，许可证 `Apache-2.0` |
| 独立 venv 执行迁移 0017 | 通过，`base → head` 与 `head → base` 均成功 |
| Git archive/sdist 内部文件排除 | 通过；计划、Prompt、`AGENTS.md`、`docs/goal-progress.md` 未进入公开包 |
| 秘密与大文件扫描 | 通过；未发现 Token/Cookie/密钥，tracked 大文件为 0 |
| `actionlint` | 通过，无诊断 |
| M9 视觉验收 | 通过，详见 [m9-visual-acceptance.md](m9-visual-acceptance.md) |

## 独立审查结论

- 版本号在 `pyproject.toml`、包 `__version__`、测试和 `uv.lock` 中一致。
- 图表只接受 verified/final `MetricResult`，并保留 data/script SHA-256 与来源 ID。
- 发布树不包含本地计划、执行 Prompt、协作约束、进度文件、凭据、数据库、论文全文或模型权重。
- M9 不包含论文、Web、Docker 真实运行或真实场景交付能力；这些边界保留在 README 和 CHANGELOG 中。

候选通过后，才允许合并 `main`、运行 main smoke、创建并推送 annotated `v0.9.0` Tag。
