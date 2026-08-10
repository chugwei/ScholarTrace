# ADR 0017：导入 Run 与最终指标必须分离

- 状态：已接受
- 日期：2026-08-11
- 范围：M7.2 Run Manifest 与现有产物导入

## 背景

现有训练项目通常只有日志、配置、权重和一个临时最佳值。若导入时直接把这个值写成最终指标，缺失的代码、数据、环境或独立评估会被掩盖。

## 决策

- Run 必须引用 frozen `ExperimentPlan` 和其中的矩阵行；所有 Artifact 引用使用相对路径，禁止路径穿越或绝对路径。
- 缺少代码 SHA、数据版本、配置、环境锁、种子、Checkpoint 或四类 Artifact 引用时，Run 状态为 `incomplete`，缺失项原样保存。
- 训练日志和手工报告导入的 `MetricResult` 固定为 `unverifiable`、`is_final=false`；不能通过导入参数绕过门禁。
- 只有后续独立评估重算才可以产生 verified/final 指标，且必须绑定评估脚本和数据版本。

## 验证

`tests/integration/test_m7_run_repository.py` 覆盖 0012 升降级、完整/不完整 Manifest、相对路径安全、重复导入和报告指标不升级。
