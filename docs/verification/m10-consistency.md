# M10.3 章节一致性与证据缺口验收

日期：2026-08-11（Asia/Shanghai）

## 本批次范围

本批次增加显式 `{{claim:id}}` 与 `{{metric:id value=x}}` 标记，检查 Claim 状态、证据缺口、MetricResult 绑定、跨章节数字一致性和 Conclusion 新 Claim。它不从普通自然语言猜测科研数字。

## 验收命令与结果

```text
uv run ruff check src tests scripts
All checks passed!

uv run pytest tests/unit/test_m10_consistency.py -q
4 passed

uv run python scripts/check.py
Ruff format/check: passed
pytest: 162 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.
```

目标测试覆盖：

- Abstract、Results、Conclusion 共享同一 verified MetricResult 时通过；
- 渲染值漂移时报告 `numeric_mismatches`；
- 未解析 metric、未支持 Claim 和 insufficient Claim 进入明确失败列表；
- Conclusion 新出现的 Claim 被标记；
- 章节生成器只输出 verified final metric 标记，拒绝未验证指标。

## 边界

测试使用合成/脱敏农业视觉指标。通过表示数字和 Claim 的结构化回溯门禁有效，不表示这些指标是真实实验结果，也不表示普通 prose 已经完成投稿级人工编辑。
