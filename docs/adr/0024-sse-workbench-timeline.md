# ADR 0024：工作台时间线复用持久事件并通过 SSE 增量更新

- 状态：accepted
- 日期：2026-08-11
- 范围：M11.2/M11.3 Run 时间线

## 决策

工作台先读取 `/api/projects/{project_id}/runs/{execution_id}/events` 建立持久快照，再以同一 Run 的 `/events/stream` 订阅增量事件。前端使用 `execution_id:sequence` 去重，并将 `Last-Event-ID` 交给浏览器的 `EventSource` 重连机制；服务端仍以 `ControlledRunRepository` 的有序事件为唯一事实来源。

页面只展示状态、事件和来源标记，不在浏览器内合并或改写 Run、Artifact、MetricResult 或 Claim。网络中断、未知 Run、非法游标和无法解析的事件都显示为降级错误，不会把连接状态解释成实验成功。

## 理由

仅依赖 SSE 会让首次打开页面时的历史事件缺失，仅依赖轮询又无法及时反映受控执行日志。快照加增量的组合既支持直接恢复，也保留事件顺序和断线重放；`sequence` 去重可以安全处理快照与重放窗口重叠的情况。

## 后续影响

工作台仍是薄客户端，真实科研结论必须由已有的证据、MetricResult 和人工审批门禁产生。当前页面使用合成/脱敏农业视觉数据完成浏览器验收，不代表真实设备、真实文献全文或部署环境已经验证。
