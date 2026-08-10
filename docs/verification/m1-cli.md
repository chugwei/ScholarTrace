# M1 CLI 验证记录

- 日期：2026-08-09（Asia/Shanghai）
- 环境：Windows，CPython 3.12.13，Typer 0.27.1
- 分支：`feat/m1-project-state`

## 验证命令与结果

```text
uv run pytest tests/integration/test_cli.py
4 passed

uv run scholartrace --help
exit 0; Chinese UTF-8 help rendered correctly

uv run python scripts/check.py
Ruff format: passed
Ruff lint: passed
pytest: 46 passed
Fixture validation: 3 synthetic fixtures passed
```

CLI 集成测试覆盖：创建项目、已完成图继续、查看项目、重复创建幂等、非法研究问题、缺失项目和缺失 checkpoint。`show` 同时断言 Repository 的 `active_stage` 与 Graph 最终状态均为 `completed`。

## 当前限制

- 本批次使用 Typer 的进程内测试 Runner；三个独立 Python 进程之间的恢复属于 M1.5；
- M1 CLI 接收结构化 JSON，不提供 LLM 自由文本补全；
- CLI 输出是本地工程接口，不代表 M11 API 或 Web 工作台已实现。
