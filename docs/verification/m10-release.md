# M10 `v0.10.0` 发布记录

日期：2026-08-11（Asia/Shanghai）

## 发布事实

- 目标仓库：[https://github.com/chugwei/ScholarTrace](https://github.com/chugwei/ScholarTrace)
- 合并提交：`33cf794707d524368deebdf18ecb4413c31d02c3`（`release: ScholarTrace v0.10.0`）
- annotated Tag：`v0.10.0`
- Tag object：`154fcbd32cc01df1dc4835af4fbe6fe77dd2fb33`
- Tag peeled commit：`33cf794707d524368deebdf18ecb4413c31d02c3`
- GitHub 分支：[main](https://github.com/chugwei/ScholarTrace/tree/main)
- GitHub Tag：[v0.10.0](https://github.com/chugwei/ScholarTrace/tree/v0.10.0)

## 发布前后验证

候选分支通过了 162 个全量测试、3 个 Fixture、Ruff、独立 wheel/venv、0018 迁移升降级、Apache-2.0、公开包和 Git archive 内部文件排除、秘密/大文件扫描、Docker actionlint 与 Python 3.12 smoke。合并后在 `main` 再次运行：

```text
uv run python scripts/check.py
Ruff format/check: passed
pytest: 162 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.
```

远端 Ref 已核验：`origin/main` 指向 `33cf794707d524368deebdf18ecb4413c31d02c3`，`refs/tags/v0.10.0` 指向 Tag object `154fcbd32cc01df1dc4835af4fbe6fe77dd2fb33`，peeled ref 指向同一 merge commit。

## 能力边界

M10 证明的是论文契约、Claim/citation/MetricResult 的离线追溯和一致性门禁。BibTeX 解析成功不等于 DOI、作者、年份或原文已经通过外部真实性核验；测试中的论文契约和指标是合成/脱敏数据。M10 不证明真实投稿论文、Web 工作台、部署或现场验证。
