# 研迹 ScholarTrace

[![quality](https://github.com/chugwei/ScholarTrace/actions/workflows/quality.yml/badge.svg?branch=main)](https://github.com/chugwei/ScholarTrace/actions/workflows/quality.yml)

研迹 ScholarTrace 是一个从研究问题、文献证据、数据与实验，到论文和真实部署的可追溯科研工作台。

当前版本为 `v0.10.0`。它包含研究问题与项目生命周期、SQLite Checkpoint、人工审批和版本审计，独立文献目录、SHA-256 去重、合法 PDF 入库、Crossref/OpenAlex 元数据查询、项目级可信证据链，版本化 PipelineSpec/DataCollectionProtocol，证据绑定的算法候选，冻结 ExperimentPlan、Run Manifest provenance、报告指标隔离、独立 MAE/RMSE/accuracy 重算和 Claim 证据门禁，受控 argv Runner、取消/超时/日志事件、失败 staging 隔离、DebugCase 审批和隔离回归，由 verified MetricResult 驱动、可重建并带数据与脚本溯源的 PNG/SVG/PDF 图表 Bundle，以及版本化 Manuscript/SectionContract/Claim Ledger、离线 BibTeX 解析、citation 缺失报告和章节数字一致性门禁。M4 的 hashing Vector、M5/M6 的合成方案、M7 的合成 Run/Metric、M8 的合成脚本、M9 的合成图表和 M10 的合成论文契约只证明离线契约；Docker、MLflow、真实农业视觉训练、真实文献召回、真实采集、投稿论文、Web 工作台和现场结果仍需独立环境或真实场景证据。

## 环境要求

- Python 3.12 或更高版本
- [uv](https://docs.astral.sh/uv/)
- Git

## 安装与验证

```bash
uv sync --all-groups
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run pytest
uv run python scripts/validate_fixtures.py
```

也可以运行与 CI 完全相同的统一门禁：

```bash
uv run python scripts/check.py
```

农业视觉黄金样例位于 `examples/agriculture-vision-project/`，三个合成、脱敏 Fixture 位于 `tests/fixtures/projects/`。它们只验证项目契约，不是研究证据、模型效果或真实场景结果。

## M1 CLI

准备符合 `ResearchQuestion` 契约的 UTF-8 JSON 后，可以运行：

```bash
uv run scholartrace project create lychee-pest-001 --question-file question.json
uv run scholartrace project continue lychee-pest-001
uv run scholartrace project show lychee-pest-001
```

默认业务数据库和 checkpoint 位于被忽略的 `.scholartrace/`。完整字段和路径选项见 [CLI 文档](docs/cli.md)。

## 项目文档

- [产品范围与非目标](docs/product-scope.md)
- [架构说明](docs/architecture.md)
- [发布路线](docs/roadmap.md)
- [需求追溯矩阵](docs/traceability-matrix.md)
- [CLI 文档](docs/cli.md)
- [贡献指南](CONTRIBUTING.md)

项目按 M0 → M12 的版本路线渐进开发。当前能力、验证证据和下一版本范围以 `IMPLEMENTATION_STATUS.md` 与发布路线为准。

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。
