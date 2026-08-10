# M7.1 实验计划与矩阵验证

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m7-experiment-registry`

## 覆盖范围

- `ExperimentPlan` 与 `ExperimentMatrixEntry` 契约；
- SQLite/Alembic 迁移 `0011` 与回滚；
- 已批准算法门禁；
- draft 幂等保存、人工冻结、拒绝和父版本历史；
- 代码 SHA、数据版本、环境锁、种子、基线、消融和停止条件的持久化。

## 实际命令与结果

```text
uv run pytest tests/integration/test_m7_experiment_repository.py -q
3 passed

uv run python scripts/check.py
122 passed
validated 3 synthetic project fixtures
ScholarTrace quality gate passed.
```

Ruff format/check 均通过。本批次没有执行训练或生成指标；计划和矩阵使用合成/脱敏农业视觉输入。

## 限制

只有 frozen 计划才可被后续 RunManifest 引用。日志、配置、权重和指标导入将在 M7.2 实现，指标独立重算与 Claim 更新将在 M7.3 实现。
