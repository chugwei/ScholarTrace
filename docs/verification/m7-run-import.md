# M7.2 Run Manifest 与结果导入验证

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m7-experiment-registry`

## 覆盖范围

- SQLite/Alembic 迁移 `0012` 与回滚；
- frozen ExperimentPlan 和矩阵行引用；
- 完整与不完整 Run Manifest；
- 相对 Artifact 路径和路径穿越阻断；
- 训练日志/报告指标的 `unverifiable`、非最终状态；
- 重复导入和身份冲突。

## 实际命令与结果

```text
uv run pytest tests/integration/test_m7_run_repository.py -q
3 passed

uv run python scripts/check.py
125 passed
validated 3 synthetic project fixtures
ScholarTrace quality gate passed.
```

Ruff format/check 均通过。没有执行训练、评估或统计重算；Run 与指标使用合成/脱敏农业视觉材料。

## 限制

当前只能导入结构化 Manifest 和已报告数值，不能把报告值当最终结果。M7.3 将增加独立指标重算、统计汇总和 Claim 更新。
