# ADR 0010：研究设计 Subgraph 在人工批准后才发布方案

- 状态：已接受
- 日期：2026-08-11
- 范围：M5.2 PipelineSpec/DataCollectionProtocol Subgraph

## 背景

结构化方案可以被校验和版本化，但 draft 仍可能包含未经确认的采样假设、授权限制或数据划分风险。自动把 draft 写成正式方案会混淆“候选设计”和“已批准设计”。

## 决策

Subgraph 按 `intake → persist_drafts → request_approval(interrupt) → apply_decision → END` 执行。批准/拒绝/取消/暂停都需要 actor 和理由，并通过既有 DecisionRecord 的 `design` target 审计。只有批准分支调用 DesignRepository 的 approve 方法；其他分支保留 draft/rejected 状态，不暴露正式方案。PipelineSpec 的阶段顺序另外渲染为确定性 Mermaid 流程图。

## 取舍

- 复用 LangGraph Checkpointer 保存暂停边界，业务版本和审计仍在 SQLite；两者职责不混淆。
- 当前 Graph 不自动修改设计字段；研究者应提交带父版本的新 draft，避免 interrupt 恢复时隐式覆盖。
- 流程图只表达设计顺序，不代表已执行采集或训练；质量/泄漏检查留给 M5.3。

## 验证

`tests/integration/test_m5_design_graph.py` 验证批准/拒绝、interrupt/resume、DecisionRecord、缺失 draft 错误和 Mermaid 输出。
