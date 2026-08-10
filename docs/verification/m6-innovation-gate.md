# M6.3 证伪计划与创新状态门禁验证

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m6-algorithm-innovation`

## 覆盖范围

- 证伪计划的确定性结构化提案；
- 基线与消融要求；
- AlgorithmSpec/PriorArtMap 批准顺序；
- `draft → approved_for_experiment → withdrawn` 以及 `rejected` 路径；
- `not_novel` 阻断和 `unverified` 边界保持。

## 实际命令与结果

```text
uv run pytest tests/integration/test_m6_algorithm_repository.py -q
8 passed

uv run python scripts/check.py
119 passed
validated 3 synthetic project fixtures
ScholarTrace quality gate passed.
```

Ruff format/check 均通过。没有运行训练、统计检验或现场验证；所有农业视觉数据和证据仍是合成/脱敏测试材料。

## 限制

`approved_for_experiment` 仅是验证入口，M7 才会提供 ExperimentPlan、Run Manifest 和指标导入。当前没有真实实验结果，也不允许据此写出“已证明创新”。
