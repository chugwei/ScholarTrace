# ADR 0011：设计批准前运行确定性质量与泄漏门禁

- 状态：已接受
- 日期：2026-08-11
- 范围：M5.3 研究设计质量检查与版本比较

## 背景

一份结构合法的方案仍可能把阶段断开，或用随机行切分导致同一来源泄漏到训练和测试。若先批准再检查，正式方案会留下不完整的审计记录。

## 决策

`validate_design_pair()` 在 `approve_design_pair()` 的同一事务前运行：PipelineSpec 检查相邻输入/输出连通；DataCollectionProtocol 要求 split strategy 和 leakage controls 明确来源/分组/会话/主体/重复边界。错误 finding 阻断批准并保持 draft。`compare_pipeline_versions()` 只报告 canonical 字段和 stage ID 差异，供人工审查，不生成“质量合格”结论。

## 取舍

- 关键词规则可离线、可复现，但不能替代真实数据样本检查；后续可增加领域插件而不改变报告契约。
- 两份设计使用一个批准事务，避免半批准状态；单独的 `approve_pipeline()` / `approve_protocol()` 仍供历史兼容测试使用。
- 版本比较不把元数据噪声算作方案变化，保留内容 SHA-256 作为完整追溯锚点。

## 验证

`tests/integration/test_m5_design_validation.py` 覆盖有效黄金样例、断开阶段、随机切分、版本差异和批准阻断。
