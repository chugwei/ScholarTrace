# M8.1 受控 Runner 契约验收

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m8-runner-debugging`

## 验收范围

本批次只验证受控执行请求、资源限制、argv 白名单、相对路径隔离、Docker 命令构造和 frozen plan 持久化门禁。尚未启动真实训练进程；启动、取消、超时、流式日志和排错属于 M8.2/M8.3。

## 命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_m8_runner_policy.py` | 通过，6 passed |
| `uv run ruff format --check src tests scripts` | 通过，95 files formatted/unchanged |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `git diff --check` | 通过 |

覆盖的边界包括：0014 升级/回滚、未冻结计划拒绝、相同 execution ID 幂等与冲突、shell 元字符/inline Python/未批准模块拒绝、绝对路径和 `..` 拒绝，以及 Docker 无网络/只读工作区/资源限制 argv 构造。

## 限制

当前环境未执行 Docker 容器或真实农业视觉训练。M8.1 的 Docker 证据是确定性命令构造测试；不能据此宣称容器资源隔离或真实场景运行已经通过。
