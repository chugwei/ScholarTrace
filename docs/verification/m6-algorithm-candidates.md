# M6.2 创新候选与方法差异验证

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m6-algorithm-innovation`

## 覆盖范围

- `InnovationCandidate` 和 `MethodDifference` 的结构化契约；
- SQLite/Alembic 迁移 `0010` 与回滚；
- 候选到 `PriorArtMap` 的项目、算法、条目和 EvidenceCard 引用一致性；
- canonical SHA-256、幂等保存和候选版本父链；
- 确定性完整度排序及“不代表创新”的输出边界。

## 实际命令与结果

```text
uv run pytest tests/integration/test_m6_algorithm_repository.py -q
6 passed

uv run python scripts/check.py
117 passed
validated 3 synthetic project fixtures
ScholarTrace quality gate passed.
```

Ruff format/check 均通过。候选、先验工作和证据均为合成/脱敏测试数据，不是已经完成的真实论文检索或真实实验。

## 限制

本批次尚未提供候选审批为实验入口的状态转换，也没有执行证伪实验；候选默认仍是 `draft` 且 `novelty_status=unverified`。M6.3 将增加基线、消融、证伪和状态门禁。
