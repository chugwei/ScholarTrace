# M8 v0.8.0 发布候选审查

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m8-runner-debugging`
- 目标版本：`v0.8.0`
- 环境：Windows，CPython 3.12.13，uv、Ruff、pytest、Docker 可用

## 范围审查

M8.1–M8.4.1 提供 frozen plan 绑定的受控 argv Runner、Docker 命令构造、异步本地生命周期、取消/超时/日志/Artifact staging、DebugCase 证据链、人工修复审批、隔离回归以及可选 JSON/MLflow/DVC 适配。M8 不宣称真实农业视觉训练、真实 MLflow 服务、真实 Docker 运行、论文、Web 或部署能力已经完成。

独立 diff 审查确认：

- 变更集中在 Runner/DebugCase/可选追踪 Schema、Repository、0014–0016 迁移、测试和公开工程文档；
- wheel 和 sdist 均显式排除 `AGENTS.md`、权威计划、执行 Prompt 和 `docs/goal-progress.md`；
- 没有加入 Token、Cookie、数据库、私有论文全文、模型权重或大型运行产物；
- 失败、取消、超时和未通过回归的运行不会发布正式 Artifact；DebugCase 只能在人工批准和回归通过后 resolved；
- `git diff --check` 无空白错误；tracked 文件大于 5MB 为 0；凭据模式匹配为 0；内部协作文件跟踪数为 0。

## 实际门禁

```text
uv run python scripts/check.py
Ruff format/check: passed
pytest: 143 passed
Fixture validation: 3 synthetic project fixtures passed

uv build --out-dir .verification/m8-rc-dist-20260811-b
scholartrace-0.8.0.tar.gz
scholartrace-0.8.0-py3-none-any.whl

sdist/wheel internal-file scan
wheel_internal: []
sdist_internal: []
wheel license: present

isolated venv wheel install/import/CLI/migration
metadata version 0.8.0; scholartrace.__version__ 0.8.0
License-Expression: Apache-2.0
scholartrace --help: exit 0
migration: 0016

docker run --rm python:3.12-slim python --version
Python 3.12.13

Docker actionlint 1.7.7
无诊断（exit 0）
```

## 真实边界

M8 目标测试使用合成/脱敏农业视觉 Run 和合成 Python 脚本。它们证明的是执行安全边界、状态恢复、证据链和发布隔离，不是模型效果、统计显著性、真实文献召回或现场部署。当前环境没有安装 MLflow，适配器实际返回 `unavailable`；DVC 只执行显式 manifest 的离线 hash 校验。

## 发布状态

本文件记录的是发布候选，不是正式版本发布证据。候选通过后还必须完成独立审查、合并到 `main`、main smoke、创建并推送 annotated `v0.8.0` Tag，再将 M8 标记为 completed。
