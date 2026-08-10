# M8.2 Runner 生命周期验收

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m8-runner-debugging`

## 验收范围

本批次验证本地受控进程的异步启动、成功/失败状态、取消、超时、日志上限、实时事件回调、事件持久化、per-run staging 和成功后的正式 Artifact 发布。执行命令仍是 M8.1 的 argv 白名单；失败、取消、超时不会发布或覆盖正式 Artifact。

## 命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_m8_runner_policy.py` | 通过，10 passed |
| `uv run python scripts/check.py` | 通过，137 passed；Fixture 校验通过 |
| `uv run ruff format --check src tests scripts` | 通过，97 files formatted/unchanged |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `git diff --check` | 通过 |

## 关键证据

- 成功脚本的 stdout 通过回调和 SQLite `controlled_run_events` 按 sequence 保存，并将 staging 输出发布到独立 Artifact 目录。
- 非零退出、超时、调用方取消和日志超限均保持正式 Artifact 目录不存在，同时 staging 和日志仍可供排错使用。
- 0015 迁移可回滚到 0014；旧 M7 迁移测试改用 `LATEST_REVISION`，全量 137 个测试通过。

## 限制

本机未实际启动 Docker 容器，也未执行真实农业视觉训练；CPU/内存硬限制目前由 Docker 命令构造提供，local backend 只强制执行超时、日志和 staging 发布边界。不能把合成脚本 E2E 描述为真实科研结果。
