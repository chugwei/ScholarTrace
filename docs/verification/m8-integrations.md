# M8.4.1 MLflow/DVC 适配验收

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m8-runner-debugging`

## 验收范围

本批次验证离线 JSON Run provenance、MLflow 可选依赖的真实可用性降级，以及 DVC-style manifest 的 SHA-256 与路径校验。没有安装付费服务或伪造外部 tracking 结果。

## 命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_m8_integrations.py` | 通过，3 passed |
| `uv run python scripts/check.py` | 通过，143 passed；Fixture 校验通过 |
| `uv run ruff format --check src tests scripts` | 通过，107 files formatted/unchanged |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `git diff --check` | 通过 |

## 真实边界

- 当前环境未安装 MLflow，适配器实际返回 `status=unavailable`，原因包含 package 未安装；这不是 tracking 成功证据。
- JSON 适配器在本地写入 Run 身份、命令 SHA-256、状态和事件计数，不写入未经验证的指标。
- DVC manifest 的匹配 hash 返回 `verified`；不匹配、缺失和逃逸路径均不会返回 verified。
