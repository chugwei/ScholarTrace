# M8.3 DebugCase 与安全修复验收

日期：2026-08-11（Asia/Shanghai）
分支：`feat/m8-runner-debugging`

## 验收范围

本批次验证失败证据捕获、错误分类、确定性假设排序、只读 staging 诊断、DebugCase 状态机、人工批准、隔离修复工作区、symlink/path/hash 防护和回归通过后才能 resolved。没有把诊断假设描述为已定位根因。

## 命令与结果

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_m8_runner_policy.py` | 通过，13 passed |
| `uv run python scripts/check.py` | 通过，140 passed；Fixture 校验通过 |
| `uv run ruff format --check src tests scripts` | 通过，103 files formatted/unchanged |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `git diff --check` | 通过 |

## 关键证据

- failed Run 只能创建 `captured` DebugCase；没有失败、取消或超时状态时创建会被拒绝。
- 假设排序在相同输入下稳定，并附带匹配关键词的 evidence reference；无匹配时返回 `unknown`。
- repair workspace 是失败 Run workspace 的副本，原始脚本保持不变；文本修复通过后，实际 `python runner_script.py` 回归命令返回 0。
- 回归失败只能进入 `regression_failed`，只有回归通过才允许 `resolved`；0016 可回滚到 0015。

## 限制

诊断目前是离线确定性检查，不调用真实 MLflow/DVC 或外部 LLM；Docker 尚未在本机实际运行，合成脚本也不是农业模型结果或真实场景证据。
