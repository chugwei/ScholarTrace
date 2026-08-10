# ADR 0023：FastAPI 只通过领域 Repository 访问状态

- 状态：accepted
- 日期：2026-08-11
- 范围：M11.1 Project/Run/Artifact API

## 决策

`create_app(database_path)` 创建隔离的 FastAPI 应用，启动时执行 Alembic head 迁移；Project、受控 Run、Run Event 和 Artifact 查询都调用现有 Repository。API 层只负责请求校验、HTTP 状态码和 JSON/SSE 序列化，不直接改写 SQLite 表，也不绕过 frozen ExperimentPlan、CommandPolicy 或 project_id 隔离。

FastAPI 版本固定在 `0.115.x`，使本地 TestClient 和 CI 行为稳定。默认数据库仍位于被忽略的 `.scholartrace/domain.db`；测试和部署可以显式传入独立路径。

## 理由

如果 Web API 另写一套状态模型，CLI、Runner 和浏览器会产生不一致。复用 Repository 保留 M1–M8 的迁移、幂等和安全门禁，应用工厂则让测试、staging 和未来服务进程使用不同数据库。

## 后续影响

M11.2 将在同一应用上增加事件流和断线后的重放；M11.3 再提供工作台页面和审批组件。当前 API 已能读写项目和受控 Run，但没有宣称浏览器垂直黄金样例完成。
