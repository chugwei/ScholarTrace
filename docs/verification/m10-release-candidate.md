# M10 `v0.10.0` 发布候选审查

日期：2026-08-11（Asia/Shanghai）

## 范围

候选版本为 `v0.10.0`，包含版本化 Manuscript、Section Contract、Claim Ledger、0018 迁移、离线 BibTeX、引用缺失报告、确定性章节草稿和 Claim/MetricResult 章节一致性门禁。候选中的论文契约与指标均为合成/脱敏数据，不是真实投稿稿件或真实科研结论。

## 验收命令与结果

| 检查 | 结果 |
|---|---|
| `uv run ruff format --check src tests scripts` | 通过，124 files already formatted |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `uv run python scripts/check.py` | 通过，162 passed；3 个合成 Fixture |
| `uv build --out-dir .verification/m10-rc-dist-20260811` | 通过，生成 `scholartrace-0.10.0.tar.gz` 和 `scholartrace-0.10.0-py3-none-any.whl` |
| wheel/sdist 内部文件排除 | 通过；计划、Prompt、`AGENTS.md`、`docs/goal-progress.md` 均为 0 |
| 独立 venv 安装 wheel、import、CLI | 通过，metadata/package version `0.10.0`，许可证 `Apache-2.0`，CLI exit 0 |
| 独立 venv 执行迁移 0018 | 通过，`head 0018`、`rollback 0017`、`head_again 0018` |
| Git archive 内部文件排除 | 通过，`archive_internal: []`，266 files |
| 秘密与大文件扫描 | 通过；Token/Cookie/密钥 0 matches，tracked >5MB 为 0 |
| Docker actionlint | 通过，1.7.7 无诊断 |
| Docker Python smoke | 通过，Python 3.12.13 |

## 独立审查结论

- 版本号在 `pyproject.toml`、包 `__version__`、测试和 `uv.lock` 中一致。
- 结果章节只允许显式绑定 verified/final MetricResult；Claim、citation 和 section contract 的缺口会保留在失败报告中。
- 公开构建不包含本地计划、执行 Prompt、`AGENTS.md`、进度文件、凭据、数据库、论文全文或模型权重。
- M10 没有宣称真实 DOI/作者/年份、真实农业实验、投稿质量、Web、部署或现场验证。

候选通过后，才允许合并 `main`、运行 main smoke、创建并推送 annotated `v0.10.0` Tag。
