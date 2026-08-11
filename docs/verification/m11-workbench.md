# M11.3 Web 工作台验收

日期：2026-08-11（Asia/Shanghai）

## 验收范围

工作台由 FastAPI 应用工厂直接提供，使用 `?project=...` 恢复已有项目状态。页面包含总览、研究问题、文献与证据、实验与 Run、论文草稿和图表六个视图；Run 时间线先读取持久事件快照，再通过 SSE 接收增量事件；论文草稿只能通过人工审阅按钮进入 `in_review`。

## 自动化结果

```text
uv run ruff format --check src tests scripts
通过

uv run ruff check src tests scripts
通过

uv run pytest tests/integration/test_m11_api.py tests/e2e/test_workbench_vertical_flow.py -q
4 passed

uv run python scripts/check.py
Ruff format/check: passed
pytest: 166 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.
```

`test_workbench_vertical_flow.py` 验证应用页面契约、研究问题保存、四个确定性 SectionContract 草稿和人工审阅状态；M11 API 测试验证 Project/Run/Artifact、事件查询、Last-Event-ID 重放和 SSE 降级。

## 浏览器验收

本地命令：

```text
uv run scholartrace web --database .verification/m11-browser.db --host 127.0.0.1 --port 8765
```

浏览器地址：`http://127.0.0.1:8765/?project=lychee-browser`

使用合成/脱敏荔枝果园演示项目实际检查到：

- URL 自动恢复项目，页面显示项目阶段 `question_defined` 和 1 条研究问题；
- “实验与 Run”显示 `execution-browser`，首屏列出 sequence 0–3 四条事件；追加事件 `live stream event received` 后，`live=true` SSE 长连接显示 sequence 4；
- “论文草稿”显示 Abstract、Methods、Results、Conclusion 四个章节，正文明确保留 “No Claim is approved” 的证据边界；
- 点击“提交人工审阅”后状态变为 `in_review`，按钮被禁用，避免重复提交；
- 页面截图和 DOM snapshot 已在本次本地浏览器验收中实际捕获，未将合成数据描述为真实农业结果。

## 限制

本验收证明浏览器、API 和 SQLite 持久状态能够完成可追溯的演示垂直流程；数据库中的 Run、计划和项目均为合成/脱敏数据。当前页面不声称真实文献全文、真实农业设备、真实训练结果或生产部署已经验证。
