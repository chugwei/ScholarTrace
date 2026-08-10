# M11 学习日志：API、SSE 与 Web 工作台

M11 把已有本地 Repository 暴露给浏览器，但 API 不是新的事实来源。M11.1 的真实代码在 `src/scholartrace/api/app.py`、`src/scholartrace/schemas/api.py` 和 `tests/integration/test_m11_api.py`。

## M11.1：Project/Run/Artifact API

`create_app(database_path)` 是应用工厂：每个测试或部署实例拥有自己的 SQLite 路径，并在启动时升级到当前迁移。Project endpoint 使用 `ProjectRepository`；Run endpoint 使用 `ControlledRunRepository`，所以没有 frozen plan 的请求仍会被拒绝；Artifact endpoint 只暴露受控 Run 已记录的 log/staging/published 路径。

State 在这一层是数据库中的项目、Run 和事件记录；Node 是 HTTP handler；Edge 是资源路由；Reducer 不是 API 的隐式合并器，状态更新必须经过 Repository 的事务；Checkpointer 仍由 LangGraph 使用，不能被 HTTP body 直接伪造。M11.2 的 SSE Tool 将读取有序事件并在断线时从 sequence 重放，M11.3 才把研究问题、文献、实验、论文和图表组合成工作台页面。

当前测试是合成/脱敏农业视觉项目，证明 HTTP 状态码、项目隔离、Run 门禁和空 Artifact 降级，不证明浏览器已经跑通真实研究流程。
