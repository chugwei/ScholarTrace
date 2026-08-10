# M1 最小持久化 Graph 验证记录

- 日期：2026-08-09（Asia/Shanghai）
- 环境：Windows，CPython 3.12.13，LangGraph 1.2.10，langgraph-checkpoint-sqlite 3.1.1
- 分支：`feat/m1-project-state`

## 验证命令与结果

```text
uv run pytest tests/integration/test_research_graph.py
5 passed

uv run python scripts/check.py
Ruff format: passed
Ruff lint: passed
pytest: 42 passed
Fixture validation: 3 synthetic fixtures passed
```

集成测试使用两个真实临时 SQLite 文件，分别保存业务实体和 checkpoint。覆盖：

- 编译图只有 `START → intake → build_research_question → save → END` 四条 Edge；
- Graph 完成后 Repository 中存在经过校验的研究问题；
- 关闭并重新打开 Graph 后，按同一 `thread_id` 读取最终 checkpoint；
- 相同输入重放后 Repository 仍只有一个研究问题版本；
- 两个 project/thread 的 checkpoint 与实体 ID 相互隔离；
- 非法研究问题触发 Pydantic 错误且不产生研究问题实体。

## 当前限制

- “重新打开”在本批次由同一 pytest 进程内关闭并重建对象验证；独立 Python 进程恢复属于 M1.5 门禁；
- M1 Graph 不调用 LLM，不声称能够从自由文本自动推导完整研究问题；
- M1 没有 Conditional Edge、`interrupt()`、`Command(resume=...)` 或人工审批，这些属于 M2。
