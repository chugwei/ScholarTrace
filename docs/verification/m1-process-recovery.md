# M1 独立进程恢复与黄金场景验收

- 日期：2026-08-09（Asia/Shanghai）
- 环境：Windows，CPython 3.12.13
- 输入：`examples/agriculture-vision-project/research-question.json`
- 数据性质：合成、脱敏的结构化农业视觉场景，不是真实研究证据

## 验证命令与结果

```text
uv run pytest tests/e2e/test_cli_process_recovery.py
4 passed in 29.66s

uv run python scripts/check.py
Ruff format: passed
Ruff lint: passed
pytest: 50 passed in 32.67s
Fixture validation: 3 synthetic fixtures passed
```

## 恢复证据

每次 CLI 调用均由 `subprocess.run` 启动新的 Python 解释器。对三个独立项目分别执行：

```text
process 1: project create
process 2: project continue
process 3: project create (replay)
process 4: project show
```

结果：

- checkpoint 重启恢复：3/3，成功率 100%；
- create、continue、replay 返回相同 `research_question_id`：3/3；
- 每个项目的研究问题记录数：1，无重复版本；
- Repository `active_stage` 与 checkpoint 最终 `active_stage`：均为 `completed`；
- 额外双项目场景中，实体 ID 不同、跨项目读取被拒绝、两个 checkpoint 返回各自 project/thread；
- 项目泄漏：0。

## 能力边界

- 这证明本地 SQLite 业务数据和 LangGraph checkpoint 可跨进程恢复；
- 输入不包含真实图像、论文、指标或现场结果；
- M1 没有人工暂停、审批、Checkpoint History 或回滚，这些属于 M2；
- M1 不证明并发多进程写入、网络文件系统或 PostgreSQL 部署能力。
