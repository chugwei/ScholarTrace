# M2 学习日志：人工澄清、审批与版本历史

截至 M2.3，缺失信息路由、持久化暂停恢复和五类人工审批已经在离线农业视觉样例中验证；研究问题冻结、历史回滚仍属于后续批次。

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

## M2.3 已验证的审批路径

`DecisionRecord` 将 `decision_id`、project/thread、目标、动作、actor、理由、结构化 payload 和时间写入独立迁移创建的 `decision_records` 表。相同决定重放返回已有记录，改变同一 ID 的内容会失败；这使网络重试不会产生重复审计事件，也不会静默覆盖历史。

`research_question_decision.py` 的真实流程是 `request_decision → apply_decision`。批准进入 `save` 并保存完整 ResearchQuestion；修改只允许已知字段，验证合并后的完整问题后再次请求人工审批；拒绝、取消和暂停结束当前流程但保留决定。荔枝病虫害样例中的“增加雨季采集约束”就是修改路径，不能被解释为已经批准，直到下一次 `approved` 记录出现。

## LangGraph 概念在本项目中的对应关系

- **State**：`ResearchProjectState` 携带项目/线程、当前问题 payload、缺口和最近动作；它只保存可序列化引用，不把论文全文或实验产物塞进 checkpoint。
- **Node**：`intake`、`request_decision`、`apply_decision` 和 `save` 各自承担一个可重放的副作用边界。
- **Edge / Conditional Edge**：固定 Edge 连接节点；`route_after_intake` 按缺口选择澄清或审批，`route_after_decision` 按人工动作选择保存、重新审批或结束。
- **Reducer**：`pending_questions` 使用替换型 reducer，表示当前缺口；`next_actions` 等列表仍使用有序去重 reducer。审计历史由数据库保存，不通过 reducer 拼接。
- **Checkpointer**：SQLite `SqliteSaver` 保存同一 `thread_id` 的等待点，关闭进程后仍可恢复；业务实体则写入独立的 Repository 数据库。
- **`interrupt()` / `Command(resume=...)`**：`request_decision` 在没有人工决定时停止；恢复必须使用同一 thread 和结构化 `Command`，不能用普通函数参数绕过审批。
- **Subgraph**：M2 还没有把审批拆成独立 Subgraph；它作为可替换的模块化 Graph 先验证边界，后续 M5 等领域子图可以复用相同审批契约。
- **Tool**：M2 没有外部工具调用。Repository 是受控的持久化边界，不等同于允许模型自由执行数据库或系统命令。

## M2.3 最小运行示例

```python
from langgraph.types import Command
from scholartrace.graphs import open_research_question_decision_graph

with open_research_question_decision_graph(domain_db, checkpoint_db) as graph:
    waiting = graph.invoke(state)
    completed = graph.resume(
        state["thread_id"],
        Command(resume={
            "decision_id": "decision-001",
            "action": "approved",
            "actor_id": "researcher-001",
            "reason": "已核对研究问题边界",
        }),
    )
```

`waiting` 只表示存在人工审批请求；只有 `completed` 且 Repository 中存在 ResearchQuestion 时，才算批准路径完成。合成 Fixture 的通过结果不等同于真实果园数据验证。
