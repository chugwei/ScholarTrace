# ADR 0003：Checkpoint 回滚使用新状态和审计记录

- 状态：已接受
- 日期：2026-08-10
- 范围：M2.5 Checkpoint History 与回滚

## 背景

LangGraph 的 checkpoint 是工作流重放和人工等待的事实记录。直接删除或覆盖旧 checkpoint 会破坏恢复证据，也无法解释某次审批为何回到较早状态。回滚还必须与研究问题领域版本区分，不能因为恢复 State 就删除已冻结的 ResearchQuestion。

## 决策

按 thread 查询 `StateSnapshot` 历史，回滚目标只能来自同一 thread。使用 `CompiledStateGraph.update_state()` 将目标值写成新的 checkpoint，并根据目标快照恢复其下一节点语义；所有旧 checkpoint 保留。回滚成功后写入 `DecisionRecord(target_type="checkpoint", action="rolled_back")`，记录来源、目标、actor、理由和恢复阶段。

## 取舍与边界

- 回滚是工作流 State 的恢复，不是数据库删除，也不撤销已经批准的研究问题版本；后续新版本必须继续使用 M2.4 的父版本门禁。
- 只接受当前 graph 能识别的物化阶段到来源节点映射；无法安全解释的 checkpoint 会拒绝回滚，而不是猜测下一步。
- 审计记录沿用 DecisionRecord 表，避免在 M2 重复建设并行事件模型；后续 RunEvent 可以在更大范围内扩展事件类型。

## 验证

`tests/integration/test_m2_decision_graph.py` 验证历史重开、回滚产生新 checkpoint、State 阶段恢复、未知 checkpoint 拒绝和 `rolled_back` 查询。测试仍使用合成、脱敏农业视觉数据，不代表现场部署结果。
