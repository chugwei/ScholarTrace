# M2 学习日志：人工澄清、审批与版本历史

M2 尚未实现。本日志先冻结学习目标和验收边界，代码与测试完成后再补充实际运行证据。

## 学习目标

- `Conditional Edge`：根据 State 中缺失字段选择澄清路径或继续路径；
- `interrupt()`：在真正需要人工决定的位置暂停图并持久化等待状态；
- `Command(resume=...)`：携带人工决定恢复同一个 `thread_id`；
- `DecisionRecord`：保存谁在何时以什么输入批准、拒绝、修改、取消或暂停；
- Checkpoint History 与回滚：区分当前 State、历史快照和可审计的领域版本。

## 农业视觉场景中的真实问题

荔枝病虫害研究可能缺少类别体系、采集授权或小目标阈值。系统不能把缺失字段猜成事实：缺失时应走 Conditional Edge，暂停并请求人工补充；批准后的研究问题必须冻结，修改应创建新版本而不是覆盖旧版本。

## 与 M1 的关系

M1 已提供可恢复 State、Repository、Checkpoint 和 CLI。M2 将在其上增加人工决策状态与版本历史，不改变 M1 已发布的固定顺序成功路径；每个审批结果都必须能够回到对应 thread、输入、版本和审计记录。

## M2.1 已验证的最小路径

`intake` 先把结构化 payload 与缺失字段写入 State，Conditional Edge 根据 `pending_questions` 选择 `clarify` 或 `build_research_question`。农业视觉黄金输入缺少 `success_criteria` 时，系统会明确列出字段并结束在 `awaiting_clarification`；它不会保存一个不完整的研究问题，也不会把 Fixture 当作证据。完整 payload 仍沿 M1 路径保存。

常见错误是把“字段存在”当成“信息完整”：空白文本、空核心列表和缺失键都被测试覆盖。M2.1 的 `pending_questions` 只描述当前缺口；后续 M2.2 会增加暂停/恢复和清理语义。

## M2.2 已验证的暂停语义

`interrupt()` 第一次执行会停止 `clarify` 节点并把请求写入 SQLite Checkpoint。恢复不是普通函数调用，而是同一 thread 上的 `Command(resume=answer)`；LangGraph 会从节点开头重放，因此节点必须保持确定性。测试关闭并重开 graph 后完成恢复，也验证了不完整回答会再次产生 interrupt。

这里仍没有“批准”结论：补充字段只是澄清输入，DecisionRecord 和冻结动作留给 M2.3–M2.4。这样可以把“恢复机制正确”和“科研审批已发生”分开验证。
