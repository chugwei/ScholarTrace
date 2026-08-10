# M7 v0.7.0 发布候选审查

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m7-experiment-registry`
- 目标版本：`v0.7.0`
- 环境：Windows，CPython 3.12.13，uv、Ruff、pytest、Docker 可用

## 范围审查

M7.1–M7.3 提供冻结的 `ExperimentPlan`/矩阵、Run Manifest 导入、完整性与相对路径门禁、报告指标的 `unverifiable` 边界、accuracy/MAE/RMSE 独立重算、verified/final 聚合和 Claim 状态降级。M7 不执行训练，不把日志临时值变成最终指标；M8–M12 的 Runner、图表、论文、Web、部署和真实场景验证不在本版本声明范围内。

独立 diff 审查确认：

- 变更集中在实验 Schema、计划/Run/Metric/Claim Repository、0011–0013 迁移、确定性指标工具、M7 测试和公开工程文档；
- 没有加入计划、Prompt、`AGENTS.md`、`docs/goal-progress.md`、Token、Cookie、数据库、私有论文全文、模型权重或大型运行产物；
- `git diff origin/main...HEAD --check` 无空白错误；tracked 文件大于 5MB 为 0；凭据模式匹配文件为 0；内部协作文件跟踪数为 0；
- 报告指标不能标记 final；没有 verified/final 结果的 Claim 自动为 `insufficient`。

## 实际门禁

```text
uv run python scripts/check.py
Ruff format/check: passed
pytest: 127 passed in 64.73s
Fixture validation: 3 synthetic project fixtures passed

uv build --out-dir .verification/m7-rc-dist
scholartrace-0.7.0.tar.gz
scholartrace-0.7.0-py3-none-any.whl

隔离 venv wheel 安装/import/CLI/迁移
metadata version 0.7.0; scholartrace.__version__ 0.7.0
scholartrace --help passed
migration 0013
wheel license: present; internal collaboration files: []

Docker actionlint 1.7.7
无诊断（exit 0）
```

GitHub Actions 状态如果因 API rate limit 无法读取，只记录为“未验证”，不猜测通过。

## 发布边界

Run、指标和 Claim 测试使用合成/脱敏农业视觉数据。它们证明的是 provenance 和状态门禁，不是实际训练效果、统计显著性或真实场景结果。`v0.7.0` 发布后 M8 才会进入受控执行与排错。

## 发布结果

- 功能分支已非 squash 合并到 `main`，merge commit：`1cd928089a203513bd3aebb2ff06c6b9c1e38221`；
- `main` 已推送并核验为 `1cd9280`，main smoke/全量门禁 127 passed；
- annotated Tag `v0.7.0` 已推送；Tag object：`95af6612c0d2a50d2d558d38faa3bed7a3eb17fa`，peeled commit：`1cd9280`；
- M7 已发布；M8–M12 仍未完成。
