# M6 v0.6.0 发布候选审查

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m6-algorithm-innovation`
- 目标版本：`v0.6.0`
- 环境：Windows，CPython 3.12.13，uv、Ruff、pytest、Docker 可用

## 范围审查

M6.1–M6.3 提供版本化 `AlgorithmSpec`、`PriorArtMap`、`InnovationCandidate`、方法差异表、EvidenceCard 绑定、确定性完整度排序、证伪计划、基线/消融要求和 `approved_for_experiment` 状态门禁。该状态只表示允许安排验证，不能表示创新成立。M7–M12 的实验结果、论文、Web、部署和真实场景验证不在本版本声明范围内。

独立 diff 审查确认：

- 变更集中在算法 Schema、验证/排序、SQLite 0009/0010 迁移、Repository、M6 测试和公开工程文档；
- 没有加入计划、Prompt、`AGENTS.md`、`docs/goal-progress.md`、Token、Cookie、数据库、私有论文全文、模型权重或大型运行产物；
- `git diff origin/main...HEAD --check` 无空白错误；tracked 文件大于 5MB 为 0；凭据模式匹配文件为 0；内部协作文件跟踪数为 0；
- `not_novel` 候选不能进入验证；`unverified` 和 `conflicting` 不会被升级为已证明创新。

## 实际门禁

```text
uv run python scripts/check.py
Ruff format/check: passed
pytest: 119 passed in 53.98s
Fixture validation: 3 synthetic project fixtures passed

uv build --out-dir .verification/m6-rc-dist-2
scholartrace-0.6.0.tar.gz
scholartrace-0.6.0-py3-none-any.whl

隔离 venv wheel 安装/import/CLI/迁移
metadata version 0.6.0; scholartrace.__version__ 0.6.0
scholartrace --help passed
migration 0010
wheel license: present; internal collaboration files: []

Docker actionlint 1.7.7
无诊断（exit 0）
```

GitHub Actions 状态如果因 API rate limit 无法读取，只记录为“未验证”，不猜测通过。

## 发布边界

M6 的算法和创新材料使用合成/脱敏农业视觉输入，不能作为真实文献、真实实验或真实场景证据。`v0.6.0` 只发布可追溯候选设计和验证门禁；实验指标必须在后续 M7 通过独立 Run 导入或执行后产生。

## 发布结果

- 功能分支已非 squash 合并到 `main`，merge commit：`01617393620713585395105b13c23f008bb2efff`；
- `main` 已推送并核验为 `0161739`，main smoke/全量门禁 119 passed；
- annotated Tag `v0.6.0` 已推送；Tag object：`9bfc324925095042d296f3430e06aa3454ec42f4`，peeled commit：`0161739`；
- M6 已发布；M7–M12 仍未完成。
