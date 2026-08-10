# M2.1 缺失信息路由验证记录

- 日期：2026-08-10（Asia/Shanghai）
- 分支：`feat/m2-human-approval`
- 环境：Windows，CPython 3.12.13，LangGraph 1.2.10

## 验证命令与结果

```text
uv run pytest tests/integration/test_m2_routing.py
8 passed

uv run python scripts/check.py
Ruff format: passed
Ruff lint: passed
pytest: 58 passed
Fixture validation: 3 synthetic fixtures passed
```

覆盖内容：

- Conditional Edge 同时暴露 `clarify` 与 `build_research_question` 两条路径；
- 空白 `problem`、空核心列表和缺失字段按固定契约顺序进入 `awaiting_clarification`；
- 不完整输入只创建项目控制记录，不保存 ResearchQuestion；
- 完整农业视觉合成 payload 沿 M1 成功路径保存；
- 每个核心字段单独缺失时都有确定性路由结果。

## 当前限制

本批次没有 `interrupt()`、`Command(resume=...)`、人工输入、DecisionRecord 或审批结果；`clarify` 到达 `END` 只是路由占位，不能声称已经暂停或恢复。
