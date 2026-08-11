# M11 学习日志：API、SSE 与 Web 工作台

M11 把已有本地 Repository 暴露给浏览器，但 API 不是新的事实来源。M11.1 的真实代码在 `src/scholartrace/api/app.py`、`src/scholartrace/schemas/api.py` 和 `tests/integration/test_m11_api.py`。

## M11.1：Project/Run/Artifact API

`create_app(database_path)` 是应用工厂：每个测试或部署实例拥有自己的 SQLite 路径，并在启动时升级到当前迁移。Project endpoint 使用 `ProjectRepository`；Run endpoint 使用 `ControlledRunRepository`，所以没有 frozen plan 的请求仍会被拒绝；Artifact endpoint 只暴露受控 Run 已记录的 log/staging/published 路径。

State 在这一层是数据库中的项目、Run 和事件记录；Node 是 HTTP handler；Edge 是资源路由；Reducer 不是 API 的隐式合并器，状态更新必须经过 Repository 的事务；Checkpointer 仍由 LangGraph 使用，不能被 HTTP body 直接伪造。M11.2 的 SSE Tool 将读取有序事件并在断线时从 sequence 重放，M11.3 才把研究问题、文献、实验、论文和图表组合成工作台页面。

当前测试是合成/脱敏农业视觉项目，证明 HTTP 状态码、项目隔离、Run 门禁和空 Artifact 降级，不证明浏览器已经跑通真实研究流程。

## M11.2：SSE 时间线与断线重放

`/events/stream` 把 `ControlledRunEvent.sequence` 映射成 SSE `id`，并发送 `event`、JSON `data`、`retry` 和 keep-alive 注释。客户端重连时带 `Last-Event-ID`，服务端只发送更大的 sequence；这使网络断开和重新连接不会把事件顺序交给前端猜测。SSE 是传输层，Run 的事实状态仍由 Repository 保存。

最小示例是先追加 `stdout` 和 `system` 两个事件，首次读取完整流，再用 `Last-Event-ID: 0` 只重放第二个事件。测试同时验证非法游标和不存在 Run 的降级路径；M11.3 将这个事件流接入浏览器工作台。

## M11.3：薄客户端工作台与垂直验收

页面不是第二套科研状态机。`refresh()` 从 Project、ResearchQuestion、Document、EvidenceCard、Run、Manuscript 和 FigureSpec Repository 读取状态；`renderTimeline()` 只把事件快照渲染成可读时间线；`EventSource` 负责接收 SSE 增量，使用 `execution_id:sequence` 去重。这样 State 仍在 SQLite，Node 是 FastAPI handler，Edge 是资源路由，Reducer 是 Repository 的事务规则，SSE 只是 Tool-like 传输通道，不能改写正式科研产物。

实际农业视觉演示使用 `lychee-browser` 项目：荔枝果园研究问题进入 `question_defined`，受控 Run 产生排队和验证事件，确定性 Manuscript SectionContract 生成四个章节，点击人工审阅后状态变为 `in_review`。页面明确展示无批准 Claim，而不是补造论文结论；在 `live=true` 长连接建立后追加事件，sequence 4 在浏览器时间线出现，说明快照与增量连接能够衔接。

常见错误包括页面直接打开但没有 `project` 参数、SSE 重放造成重复事件、未知 Run 反复报错，以及把 `in_review` 误认为已批准。URL 恢复、`execution_id:sequence` 去重、HTTP 404/400 降级和禁用重复审阅按钮分别覆盖这些边界。浏览器验收详见 `docs/verification/m11-workbench.md`。
