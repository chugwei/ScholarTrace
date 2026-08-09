# M1 Project Repository 验证记录

- 日期：2026-08-09（Asia/Shanghai）
- 环境：Windows，CPython 3.12.13，SQLite，SQLAlchemy 2.0.51，Alembic 1.19.1
- 分支：`feat/m1-project-state`

## 验证命令与结果

```text
uv run pytest tests/integration/test_project_repository.py
12 passed

uv run python scripts/check.py
Ruff format: passed
Ruff lint: passed
pytest: 37 passed
Fixture validation: 3 synthetic fixtures passed

uv build
sdist and wheel built successfully

fresh venv + wheel install + upgrade_database
installed successfully; current revision: 0001
```

集成测试使用 pytest 临时目录中的真实 SQLite 文件，不使用内存替身。覆盖：

- 初始迁移重复 upgrade、downgrade 到 base、重新 upgrade；
- 相同 `project_id/thread_id` 的幂等创建与关闭后重开；
- project/thread 身份冲突后的事务回滚和后续写入；
- 不安全或超长标识符拒绝且不产生记录；
- 相同研究问题重放不增加版本，内容变化增加版本；
- 同一内容在两个项目中的实体隔离；
- 缺失项目时不留下部分研究问题记录。

构建后的 wheel 已确认包含 `persistence/migrations` 下的 Alembic 环境与初始 revision，并在独立 venv 中从已安装包实际执行迁移。

## 当前限制

- 本批次只验证业务 Repository，不代表 LangGraph Checkpoint 已持久化；
- 当前只提供初始 Schema，M2 才加入冻结、审批、回滚和完整审计实体；
- 本批次没有使用或生成真实科研数据，SQLite 文件均为测试临时产物且未进入 Git。
