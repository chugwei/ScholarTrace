# M11.1 Project/Run/Artifact API 验收

日期：2026-08-11（Asia/Shanghai）

## 验收命令与结果

```text
uv run ruff format --check src tests scripts
128 files already formatted

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

目标测试覆盖 Project 创建/幂等/list/get/404 隔离、绑定 frozen plan 的受控 Run 创建、空 Artifact 降级、事件查询和 SSE keep-alive。FastAPI 只通过 Repository 访问数据库；缺少项目、计划或不匹配的 project_id 会返回明确 HTTP 错误。

## 边界

本批次没有完成前端页面、浏览器垂直流程或真实场景验证。Run 测试使用合成计划和安全的 `python -m pytest` argv，只证明 API 与既有受控执行契约一致。
