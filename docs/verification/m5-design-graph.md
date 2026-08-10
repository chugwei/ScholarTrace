# M5.2 研究设计 Subgraph 与流程图验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m5-pipeline-data-design`
- 环境：Windows，CPython 3.12.13，SQLite，LangGraph SQLite Checkpointer
- 数据性质：合成/脱敏农业视觉方案，不是真实采集或实验结果

## 已执行命令

```text
uv run pytest tests/integration/test_m5_design_graph.py -q
3 passed

uv run ruff format --check src tests scripts
67 files already formatted

uv run ruff check src tests scripts
All checks passed!

uv run python scripts/check.py
pytest: 105 passed in 43.52s
Fixture validation: 3 synthetic project fixtures passed
```

## 覆盖范围

- Subgraph 能在同一 thread 的 `interrupt()` 后用 `Command(resume=...)` 恢复；
- 批准同时发布 PipelineSpec 和 DataCollectionProtocol，写入 `design` DecisionRecord；
- 拒绝路径保留 rejected 状态，未批准设计不会被描述为正式方案；
- 缺失任一 draft 会在入口失败；
- PipelineStage 顺序生成稳定 Mermaid flowchart。

## 限制

本批次还没有数据质量/泄漏执行检查、版本差异报告、Markdown/YAML 导出或真实人工采集。Subgraph 的通过只证明状态、暂停恢复和审计契约，不证明方案适合任何真实果园。
