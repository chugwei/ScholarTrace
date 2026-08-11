# ADR 0029：真实场景验证的证据分层与字段门禁

- 状态：accepted
- 日期：2026-08-11
- 范围：M12.5 真实场景验证记录、证据分层边界和字段级门禁

## 决策

把 `synthetic_fixture`、`offline_test`、`staging`、`real_field` 四个证据等级从 `DeliveryEvidence` 的声明性字段升级为有结构边界的契约。新增 `FieldValidationRecord`、`FieldValidationSummary`、`FieldEnvironmentContext`、`FieldProvenance` 和 `RollbackOutcome`，并施加以下门禁：

1. 非 `real_field` 记录禁止携带 `FieldEnvironmentContext`，避免合成/离线/Staging 记录混入现场字段而被读成田间证据。
2. `real_field` 记录必须同时提供 `FieldEnvironmentContext` 和 `FieldProvenance`；缺任一项不可创建。
3. `FieldEnvironmentContext` 的 `operator_name` 和 `ethics_approval_ref` 为必填，因为无操作人员和无伦理批准的现场主张不可验证。
4. `FieldValidationSummary` 的 `conclusion_class` 为 `real_field` 时，只接受全部由 `real_field` 记录组成的集合，且记录不能为空。
5. `RollbackOutcome.attempted` 为真时必须记录最终 `active_release_id`，避免回滚后无法定位当前版本。

## 理由

合成、离线和 Staging 结果在科研交付中有各自价值，但都不能支持“已用于真实场景”。如果这些结果可以自由携带现场字段，就会在 Model Card、交付 Manifest 或发布说明里被误读为田间证据。用 Pydantic `model_validator` 在类型层把“层级”和“可携带字段”绑定，比依赖文档约定或运行后检查更难绕过。

把伦理批准、操作人员、隐私审查设为必填，对应权威计划对真实场景验证的硬性要求：真实数据需要来源、设备、环境、伦理确认、操作人员、时间以及代码/数据/模型版本。在用户提供这些输入之前，`real_field` 路径无法构造合法记录，Goal 不会被合成结果提前关闭。

## 后续影响

- 真实场景验证记录由用户提供数据、设备和现场操作后填写；本仓库不伪造这些字段。
- `FieldValidationSummary` 可用于发布说明和 Model Card，但 `real_field` 结论必须由独立审查确认。
- 生产级多地点、多季节验证、监管提交和长期监控不在 M12.5 范围；M12.6 需要在独立环境复跑安装、部署、回滚和分层验证，才能发布 `v1.0.0`。
