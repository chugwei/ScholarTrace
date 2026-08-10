# M2.3 DecisionRecord 与审批图验证记录

- 日期：2026-08-10（Asia/Shanghai）
- 分支：`feat/m2-human-approval`
- 环境：Windows，CPython 3.12.13，LangGraph 1.2.10，langgraph-checkpoint-sqlite 3.1.1

## 验证命令与结果

```text
uv run pytest tests/integration/test_m2_decision_record.py tests/integration/test_m2_decision_graph.py -q
11 passed

uv run pytest -q
73 passed

uv run ruff format --check src tests scripts
38 files already formatted

uv run ruff check src tests scripts
All checks passed

uv run python scripts/validate_fixtures.py
validated 3 synthetic project fixtures
```

## 覆盖内容

- `0002` 迁移可重复升级；从 `0002` 回退到 `0001` 会移除 `decision_records`，再回退到 base 后可重新升级；
- DecisionRecord 对五种动作、非批准理由、未知字段和审计字段做结构校验；
- 相同 `decision_id` 的相同内容重放幂等，内容冲突显式失败，项目和 thread 作用域隔离；
- 农业视觉研究问题的批准、拒绝、修改、取消和暂停路径均通过真实 `interrupt()` / `Command(resume=...)` 运行；
- 修改动作只能写入 ResearchQuestion 已知字段，合并后重新进入审批；终止动作不会保存未批准的研究问题；
- 业务数据库与 SQLite Checkpoint 分离，DecisionRecord 可以在重开 Repository 后查询。

## 限制

本批次验证使用合成、脱敏的农业视觉 Fixture，不是现场果园数据；研究问题冻结、新版本、Checkpoint 历史与回滚查询仍未完成，因此 M2 整体尚未发布。
