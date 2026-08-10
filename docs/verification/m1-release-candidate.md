# M1 v0.1.0 发布候选审查

- 审查提交：`52bf99f3f2e6974e8ea175f43e571f819e4fde0b`
- 发布合并提交：`986eee31fbf16d534e4e84b8f7cb3338e353d6d9`
- 分支：`main`
- 日期：2026-08-10（Asia/Shanghai）
- 目标版本：`v0.1.0`

## 范围与实现

发布候选包含 M1.1–M1.5：ResearchQuestion/State/Reducer、SQLite Project Repository 与 Alembic 迁移、固定顺序 LangGraph、SQLite Checkpointer、CLI create/continue/show、独立进程恢复、幂等和农业视觉合成黄金样例。M2 及后续文献、实验、论文、Web 和部署能力不在本版本声明范围内。

## 独立源码验收

使用 `git archive 52bf99f` 创建隔离源码目录后执行：

```text
uv sync --frozen --all-groups                 passed
uv run python scripts/check.py                passed; 50 tests
uv build                                      passed; sdist + wheel 0.1.0
```

隔离副本中的测试结果：Ruff format passed、Ruff lint passed、50 passed、3 个合成 Fixture 校验通过。源代码安装、迁移、CLI 和跨进程 E2E 均从该快照运行。

## 独立 wheel 验收

在新的 Python 3.12 venv 中只安装 `scholartrace-0.1.0-py3-none-any.whl` 及其锁定依赖：

- 包版本：`0.1.0`；
- `License-Expression`：`Apache-2.0`；
- `python -m scholartrace --help`：UTF-8 帮助通过；
- Alembic：`0001 → base → 0001` 通过；
- wheel CLI：create/continue/show 跨进程通过；
- wheel Checkpoint 与业务问题 ID 一致，问题记录数为 1，项目阶段为 `completed`。

## 安全、迁移与 CI

- 历史和候选树中的 Secret 模式：0；
- 内部计划、执行指令和本地进度文件路径：0；
- 数据库、模型权重、运行产物和私有文献：0 个跟踪文件；
- 最大跟踪文件为 `uv.lock`，约 240 KB；
- `actionlint` Docker 对 `.github/workflows/quality.yml` 无诊断；
- GitHub Actions quality Run #14：成功，提交 `52bf99f`；
- GitHub Actions quality Run #16：成功，合并提交 `986eee3`；
- M1.1–M1.5 对应远端 quality Runs #8、#10、#11、#12、#13、#14：均成功。

依赖漏洞服务审计曾执行 `pip-audit --path`，但 PyPI 请求在 15 秒读取超时；该项记为“未验证”，没有被包装成通过。它不改变本地锁定安装、代码秘密扫描或测试结果的事实。

## 发布决策

M1 功能、测试、迁移、独立环境、CLI、E2E、秘密扫描和 CI 门禁已满足。功能分支已通过非 squash 合并进入 `main`，合并提交 `986eee3` 的 main smoke test 和 Run #16 均通过；annotated Tag `v0.1.0` 已推送，远端 tag 对象为 `a7ef171`，peeled commit 为 `986eee3`。M1 已发布，后续进入 M2。
