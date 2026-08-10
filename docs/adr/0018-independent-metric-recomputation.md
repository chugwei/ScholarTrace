# ADR 0018：最终指标只来自独立重算

- 状态：已接受
- 日期：2026-08-11
- 范围：M7.3 指标重算、统计汇总和 Claim 更新

## 背景

训练日志中的最佳值可能来自训练集、不同阈值或不同数据版本，不能直接支撑论文结果。M7 需要把“报告的数值”和“按固定协议重新计算的数值”放在不同状态。

## 决策

- `recompute_metric()` 只接受显式 predictions/targets，当前提供确定性的 accuracy、MAE 和 RMSE；不读取日志，也不补齐缺失数据。
- `record_recomputed_metric()` 要求 Run 完整、计划 frozen、数据版本一致、评估脚本 SHA 存在，才写 `verified`/`is_final=true`。
- 统计汇总只查询 verified/final `MetricResult`，使用固定 population standard deviation；没有 verified 结果就失败。
- Claim 请求 `supported`/`contradicted` 时，如果绑定结果不全是 verified/final，实际状态降级为 `insufficient`，并保留原因。
- Claim 更新追加写入，不覆盖历史，也不自动写论文正文。

## 验证

`tests/integration/test_m7_run_repository.py` 覆盖重算值、汇总均值/标准差、数据版本阻断、报告值降级和 Claim 状态门禁。
