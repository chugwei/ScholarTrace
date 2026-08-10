# M2.5 Checkpoint History、回滚与审计验证记录

- 日期：2026-08-10（Asia/Shanghai）
- 分支：`feat/m2-human-approval`
- 环境：Windows，CPython 3.12.13，LangGraph 1.2.10，langgraph-checkpoint-sqlite 3.1.1

## 验证命令与结果

```text
uv run pytest tests/integration/test_m2_decision_graph.py tests/integration/test_m2_decision_record.py -q
13 passed

uv run python scripts/check.py
Ruff format: 39 files already formatted
Ruff lint: All checks passed
pytest: 76 passed
Fixture validation: 3 synthetic fixtures passed
```

## 覆盖内容

- 同一 thread 的 StateSnapshot 历史按新到旧查询，关闭并重开 graph 后仍可读取；
- 从批准后的 completed 状态回滚到审批前的 awaiting_approval checkpoint，恢复后的 State 不包含已保存的 `research_question_id`；
- 回滚写入新的 checkpoint，历史目标和来源 checkpoint 都保留；
- 缺失 checkpoint ID 被拒绝，不会产生审计记录；
- `rolled_back` DecisionRecord 保存 checkpoint target、actor、理由和来源/目标 payload，并支持 `list_decisions(action=...)` 查询；
- 回滚不删除业务数据库中已经批准的研究问题版本。

## 限制

本批次只验证研究问题审批图的 checkpoint 回滚，尚未为 CLI 或 Web API 暴露回滚入口；M2.6 发布审查、合并 main 和 `v0.2.0` Tag 尚未完成。验证使用合成、脱敏 Fixture，不等同于真实场景证据。
