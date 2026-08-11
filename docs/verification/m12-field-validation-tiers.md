# M12.5 真实场景验证记录与证据分层验收

日期：2026-08-11（Asia/Shanghai）

## 范围

本批次为交付阶段建立真实场景验证记录契约，把 `synthetic_fixture`、`offline_test`、`staging` 和 `real_field` 四个证据等级从声明性字段升级为强制性的结构边界。目标是让合成、离线和 Staging 结果无法被包装成真实场景结论，同时为用户后续提供的真实数据、设备和现场操作预留可填写的记录模板。

本批次不产生真实场景证据。所有示例记录都使用 `synthetic_fixture` 或 `staging` 等级，明确声明不是田间结果。

## 证据分层

| 等级 | 含义 | 是否支持“已用于真实场景” |
|---|---|---|
| `synthetic_fixture` | 合成/脱敏 Fixture、契约演示 | 否 |
| `offline_test` | 离线单元/集成测试、固定回归集 | 否 |
| `staging` | 本地 Compose/Staging smoke、容器健康推理 | 否 |
| `real_field` | 真实现场数据、真实设备、真实操作人员 | 是 |

只有 `real_field` 支持“已用于真实场景”的表述。这是权威计划的硬性要求，不是可选项。

## 设计与验证

- `FieldEnvironmentContext` 记录现场地点、设备、采集条件、操作人员、隐私审查和伦理批准编号；`operator_name` 与 `ethics_approval_ref` 为必填，缺项不可发布为 `real_field`。
- `FieldProvenance` 记录代码版本、数据版本、模型版本和交付 Manifest 绑定，保证现场结果可以回到产生它的代码和数据。
- `FieldValidationRecord` 用 `model_validator` 强制：非 `real_field` 等级禁止携带现场环境上下文；`real_field` 必须同时带完整 environment 和 provenance。
- `FieldValidationSummary` 用 `conclusion_class` 聚合记录，并禁止把低层级记录汇总为 `real_field` 结论；`record_count_by_class` 列出全部四类的计数，避免“缺失即零”的歧义。
- `RollbackOutcome` 记录验证过程中是否触发了 release 回滚，并要求回滚发生时记录最终 active release。

## 验收命令与结果

```text
uv run pytest tests/unit/test_m12_field_validation.py -q
6 passed
```

测试覆盖：合成记录携带现场环境被拒、Staging 记录携带现场环境被拒、`real_field` 缺少 environment 或 provenance 被拒、environment 缺少伦理批准或操作人员被拒、`real_field` 结论只接受 `real_field` 记录、混合低层级记录按类计数且不能升级为 `real_field`。

## 证据边界

当前仓库无真实场景数据、设备或现场操作。本批次交付的是记录契约和分层门禁，不是真实场景证据。`FieldValidationRecord` 的 `real_field` 路径已经有强制字段和测试保护，但需要用户提供以下输入后才能产生真正的 `real_field` 记录：

- 真实数据来源与采集协议；
- 真实设备与环境描述；
- 伦理/隐私批准编号和脱敏审查记录；
- 现场操作人员与时间；
- 对应的代码、数据和模型版本；
- 现场验证期间的回滚结果（如有）。

在这些输入到位前，Goal 保持进行中，不把合成/离线/Staging 结果描述为真实场景交付。
