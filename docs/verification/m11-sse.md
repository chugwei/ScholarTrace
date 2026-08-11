# M11.2 SSE Run 时间线验收

日期：2026-08-11（Asia/Shanghai）

## 本批次范围

Run Event 通过 `text/event-stream` 输出，保留 sequence、event name、JSON data、`retry: 3000` 和 keep-alive。默认请求是有限、可测试的快照流；工作台显式使用 `live=true`，服务端轮询同一 Repository 并保持长连接，避免有限流结束后浏览器无意义地反复重连。客户端可用 `Last-Event-ID` 或 `after_sequence` 重放未消费事件；非法游标返回 400，未知 Run/项目返回 404。

## 验收命令与结果

```text
uv run ruff check src tests scripts
All checks passed!

uv run pytest tests/integration/test_m11_api.py -q
3 passed

uv run python scripts/check.py
Ruff format/check: passed
pytest: 165 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.
```

测试使用两个有序合成 Run Event，验证完整流、从 sequence 0 重放第二事件、`retry`/keep-alive 以及非法 `Last-Event-ID`。SSE 仍读取已有 Repository，不改变 Run 状态，也不会把连接断开误报成 Run 成功。

## 边界

当前实现同时提供可重放的持久事件快照流和工作台使用的 `live=true` 增量流；浏览器页面和完整黄金样例垂直流程的证据见 `docs/verification/m11-workbench.md`。没有真实农业设备或真实部署证据。
