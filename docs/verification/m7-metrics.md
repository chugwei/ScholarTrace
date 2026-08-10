# M7.3 独立指标重算与 Claim 更新验证

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m7-experiment-registry`

## 覆盖范围

- accuracy/MAE/RMSE 确定性重算；
- frozen plan、完整 Run 和 data version 一致性；
- verified/final MetricResult 写入；
- 只聚合 verified/final 结果并计算均值、population stddev；
- 支持 Claim 与不足证据 Claim 的状态分离；
- 0013 Claim 更新迁移回滚。

## 实际命令与结果

```text
uv run pytest tests/integration/test_m7_run_repository.py -q
5 passed

uv run python scripts/check.py
127 passed
validated 3 synthetic project fixtures
ScholarTrace quality gate passed.
```

Ruff format/check 均通过。数值来自合成/脱敏 Fixture，不能被描述为真实农业实验指标。

## 限制

当前只支持小型确定性指标重算，尚未接入完整模型评估脚本、统计检验库或真实 Checkpoint。M8 才会提供受控执行，M10 才会消费 Claim Ledger 生成论文章节。
