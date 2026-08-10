# M2 v0.2.0 发布候选审查

- 日期：2026-08-10（Asia/Shanghai）
- 分支：`feat/m2-human-approval`
- 目标版本：`v0.2.0`
- 环境：Windows，CPython 3.12.13，uv、Ruff、pytest、Docker 可用

## 范围审查

发布候选包含 M2.1–M2.5：缺失信息路由、真实 `interrupt()` / `Command(resume=...)`、DecisionRecord 五类人工决定、研究问题冻结与显式新版本、Checkpoint History、受控回滚和审计查询。M3 文献库、M4 RAG、实验、论文、Web、部署和真实场景验证不在本版本能力声明内。

独立 diff 审查确认：

- 变更集中在 `src/scholartrace/`、M2 测试、迁移和公开工程文档；
- 没有加入计划、Prompt、`AGENTS.md`、`docs/goal-progress.md`、Token、Cookie、数据库、论文全文、模型权重或大型运行产物；
- `git diff main...HEAD --check` 无空白错误；
- 迁移可重复升级，并已通过 `0003 → 0002 → 0001 → base → head` 回滚验证；
- 旧 M1 固定顺序 Graph、CLI 和跨进程恢复仍通过。

## 实际门禁

```text
uv run python scripts/check.py
Ruff format: 39 files already formatted
Ruff lint: All checks passed
pytest: 76 passed
Fixture validation: 3 synthetic fixtures passed

uv run pytest tests/integration/test_m2_decision_record.py tests/integration/test_m2_decision_graph.py -q
13 passed

uv build
sdist and wheel built successfully; package version 0.2.0

独立 wheel venv 安装/import/CLI/迁移
version 0.2.0; scholartrace --help passed; migration 0003 passed

docker run --rm -v <workspace>:/repo -w /repo rhysd/actionlint:latest
passed, no diagnostics

tracked secret/personal-path scan
0 matches; tracked files >5MB: 0
```

`pip-audit` 仍因当前环境访问 PyPI 超时未验证；GitHub Actions API 当前因 SSL 连接失败未读取，因此 CI 状态不能猜测为通过。发布 Tag 只在功能分支推送、合并 `main`、本地 smoke test 和远端 Ref 核验后创建。

## 发布结果

- 功能分支已非 squash 合并到 `main`，merge commit：`668957271a6b7253a62984bb07ee62a3fdd197bf`；
- `main` 已推送并核验为 `6689572`；
- annotated Tag `v0.2.0` 已推送；Tag object：`f4990a7d3ca8ea65b0b3c90910a73ba8ac72e6bb`，peeled commit：`6689572`；
- M2 已发布；M3 文献库及后续能力仍未实现。

## 能力边界

测试使用合成、脱敏农业视觉 Fixture，证明的是结构化流程、恢复和审计契约，不是真实果园现场验证。M2 不是完整产品交付，后续 M3–M12 仍必须按路线实现和验收。
