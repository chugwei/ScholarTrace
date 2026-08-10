# M5 v0.5.0 发布候选审查

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m5-pipeline-data-design`
- 目标版本：`v0.5.0`
- 环境：Windows，CPython 3.12.13，uv、Ruff、pytest、Docker 可用

## 范围审查

发布候选包含 M5.1–M5.4：版本化 PipelineSpec/DataCollectionProtocol、人工批准研究设计 Subgraph、Mermaid 流程图、结构质量/泄漏门禁、版本差异比较，以及只允许 approved 成对设计的 Markdown/YAML 导出。M6–M12 的算法创新、实验、论文、Web、部署和真实场景验证不在本版本声明范围内。

独立 diff 审查确认：

- 变更集中在 `src/scholartrace/design/`、设计 Schema/Repository、研究设计 Graph、0008 迁移、M5 测试和公开工程文档；
- 没有加入计划、Prompt、`AGENTS.md`、`docs/goal-progress.md`、Token、Cookie、数据库、私有论文全文、模型权重或大型运行产物；
- `git diff origin/main...HEAD --check` 无空白错误，秘密/个人路径扫描为 0，tracked 文件大于 5MB 为 0；
- 未通过结构/泄漏门禁的设计保持 draft，draft 不进入正式导出；M4 既有证据链和恢复测试保持通过。

## 实际门禁

```text
uv run python scripts/check.py
Ruff format: 71 files already formatted
Ruff lint: All checks passed
pytest: 111 passed in 45.73s
Fixture validation: 3 synthetic project fixtures passed

uv build --out-dir .verification/m5-rc-dist
scholartrace-0.5.0.tar.gz
scholartrace-0.5.0-py3-none-any.whl

隔离 venv wheel 安装/import/CLI/迁移
version 0.5.0; __version__ 0.5.0; License-Expression Apache-2.0
PyYAML 6.0.3
scholartrace --help passed
migration 0008

Docker actionlint
server 28.3.2; no diagnostics
```

wheel 中包含 `dist-info/licenses/LICENSE`，且不包含内部协作文件。GitHub Actions API 若返回 rate limit，CI 状态保持“未验证”，不猜测通过。

Tag 只在功能分支推送、合并 `main`、main smoke test 和远端 Ref 核验后创建。当前文档记录的是候选，不是已经发布的 Tag。

## 能力边界

所有设计、流程图、回归和导出样例均为合成/脱敏输入。结构质量/泄漏关键词门禁不等于真实样本质量，YAML/Markdown 导出不等于数据采集已执行；真实授权、现场数据和 M12 交付验证仍未完成。
