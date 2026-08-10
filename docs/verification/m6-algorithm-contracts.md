# M6.1 算法规格与先验工作地图验证

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m6-algorithm-innovation`

## 覆盖范围

- `AlgorithmSpec`、`PriorArtEntry` 和 `PriorArtMap` 结构化契约；
- SQLite/Alembic 迁移 `0009`；
- canonical SHA-256、幂等保存、递增版本和父版本约束；
- EvidenceCard 存在性门禁；
- 算法规格先于先验工作地图批准；
- 项目隔离和迁移回滚。

## 实际命令与结果

```text
uv run pytest tests/integration/test_m6_algorithm_repository.py -q
4 passed

uv run python scripts/check.py
115 passed
validated 3 synthetic project fixtures
ScholarTrace quality gate passed.
```

Ruff format/check 均通过。测试中的证据和农业视觉项目均为合成/脱敏 Fixture，不是公开论文真实性或现场科研结果的证明。

## 限制

本批次尚未实现 `InnovationCandidate`、方法差异排序、证伪实验设计或实验执行；算法记录也不宣称创新成立。M6.2/M6.3 将在此基础上继续增加候选契约和状态门禁。
