# M2.2 interrupt/resume 验证记录

- 日期：2026-08-10（Asia/Shanghai）
- 分支：`feat/m2-human-approval`
- 环境：Windows，CPython 3.12.13，LangGraph 1.2.10，langgraph-checkpoint-sqlite 3.1.1

## 验证命令与结果

```text
uv run pytest tests/integration/test_m2_interrupt_resume.py
4 passed

uv run python scripts/check.py
Ruff format: passed
Ruff lint: passed
pytest: 62 passed
Fixture validation: 3 synthetic fixtures passed
```

覆盖内容：

- `pending_questions` 替换型 Reducer 清理旧缺口并保持有序去重；
- 第一次 invoke 返回 `__interrupt__`，请求包含缺失字段和当前 payload；
- 关闭并重开 graph 后，用同一 thread 的 `Command(resume=...)` 完成保存；
- 不完整恢复回答会再次 interrupt，ResearchQuestion 记录仍为 0；
- checkpoint snapshot 在重开后仍报告等待 task 和 interrupt。

## 当前限制

本批次的 resume 只补充结构化研究问题字段，不代表用户已经批准研究问题；DecisionRecord、批准/拒绝/修改/取消/暂停语义和版本冻结属于 M2.3–M2.4。
