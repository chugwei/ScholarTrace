# ADR 0009：研究设计使用不可隐式覆盖的版本化契约

- 状态：已接受
- 日期：2026-08-11
- 范围：M5.1 PipelineSpec 与 DataCollectionProtocol

## 背景

研究方案会随着文献证据、数据授权和失败分析变化。直接修改一份 JSON/Markdown 会丢失当时的采样、划分和风险假设，批准后的方案也可能被静默替换。

## 决策

PipelineSpec 和 DataCollectionProtocol 使用 Pydantic 结构契约、canonical content SHA-256、递增版本、父版本和 `draft/approved/rejected/superseded` 生命周期。新记录先是 draft；批准保存 actor、理由和时间，并将旧批准版本标为 superseded。已批准版本不能被普通保存覆盖，后续修改必须声明当前批准父版本。SQLite 0008 将结构化 payload 与关键查询列同时保存，并支持回滚。

## 取舍

- JSON payload 便于 Schema 演进和导出，关键状态列便于查询；未来迁移仍需兼容测试。
- M5.1 不自动调用 LLM 或外部采集服务，避免把候选方案冒充已执行方案。
- 版本号和父 ID 由 Repository 强制，调用者不能通过传入 `approved` 状态绕过人工门禁。

## 验证

`tests/integration/test_m5_design_repository.py` 覆盖 0008 升降级、Schema 唯一性、版本幂等、人工批准/拒绝、父版本和跨项目隔离。
