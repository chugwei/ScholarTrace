# 需求追溯矩阵

状态含义：`implemented-tested`、`implemented-unverified`、`contract-only`、`planned`、`blocked`。

| 计划需求 | 实现 | 测试/证据 | 版本 | 状态 |
|---|---|---|---|---|
| M0 Python 3.12 + uv + src layout | `pyproject.toml`, `.python-version`, `src/scholartrace/` | `tests/unit/test_package.py`, `uv.lock` | v0.0.1 | implemented-tested |
| M0 范围与非目标 | `docs/product-scope.md` | 文档审查 | v0.0.1 | implemented-unverified |
| M0 科研真实性与数据安全 | `docs/research-integrity.md` | 文档审查、秘密扫描 | v0.0.1 | implemented-unverified |
| M0 风险登记 | `docs/risk-register.md` | 文档审查 | v0.0.1 | implemented-unverified |
| M0 ADR 机制 | `docs/adr/0001-progressive-evidence-first-architecture.md` | 文档审查 | v0.0.1 | implemented-unverified |
| M0 架构与学习日志 | `docs/architecture.md`, `docs/learning-log/m0-foundations.md` | `docs/verification/m0-review.md` | v0.0.1 | implemented-tested |
| M0 全新环境安装与构建 | `pyproject.toml`, `uv.lock` | `docs/verification/m0-release-candidate.md` | v0.0.1 | implemented-tested |
| M0 3 个脱敏 Fixture | `tests/fixtures/projects/`, `src/scholartrace/fixtures.py`, `examples/agriculture-vision-project/` | `tests/unit/test_fixtures.py`, `tests/integration/test_fixture_catalog.py`, `scripts/validate_fixtures.py` | v0.0.1 | implemented-tested |
| M0 CI | `.github/workflows/quality.yml`, `scripts/check.py` | [quality Run #1](https://github.com/chugwei/ScholarTrace/actions/runs/31313652417) | v0.0.1 | implemented-tested |
| M0 LICENSE | `LICENSE`, `pyproject.toml`, `README.md` | `tests/unit/test_package.py`, wheel 内容检查 | v0.0.1 | implemented-tested |
| M0 发布 | `CHANGELOG.md`, `docs/verification/m0-release.md` | quality Run #4、annotated Tag `v0.0.1` | v0.0.1 | implemented-tested |
| M1–M12 | `docs/roadmap.md` | 尚未实现 | v0.1.0–v1.0.0 | planned |
| M1 State/ResearchQuestion/Reducer | `src/scholartrace/schemas/research.py`, `src/scholartrace/states/research_project.py` | `tests/unit/test_research_question.py`, `tests/unit/test_research_project_state.py` | v0.1.0 | implemented-tested |
| M1 SQLite Repository/迁移 | `src/scholartrace/persistence/` | `tests/integration/test_project_repository.py`, `docs/verification/m1-repository.md` | v0.1.0 | implemented-tested |
| M1 最小 Graph/Checkpointer | `src/scholartrace/graphs/research_project.py` | `tests/integration/test_research_graph.py`, `docs/verification/m1-graph.md` | v0.1.0 | implemented-tested |
| M1 CLI create/continue/show | `src/scholartrace/cli.py`, `pyproject.toml` | `tests/integration/test_cli.py`, `docs/verification/m1-cli.md` | v0.1.0 | implemented-tested |
| M1 独立进程重启恢复 | `src/scholartrace/__main__.py`, `examples/agriculture-vision-project/research-question.json` | `tests/e2e/test_cli_process_recovery.py`, `docs/verification/m1-process-recovery.md` | v0.1.0 | implemented-tested |
| M1 发布候选与独立环境 | `pyproject.toml`, `uv.lock`, `docs/verification/m1-release-candidate.md` | Git archive、wheel、Run #14、actionlint、秘密扫描 | v0.1.0 | implemented-tested |
| M2.1 缺失信息路由 | `src/scholartrace/graphs/research_question_review.py` | `tests/integration/test_m2_routing.py`, `docs/verification/m2-routing.md` | v0.2.0 | implemented-tested |
| M2.2 interrupt/resume | `src/scholartrace/graphs/research_question_approval.py`, `src/scholartrace/states/research_project.py` | `tests/integration/test_m2_interrupt_resume.py`, `docs/verification/m2-interrupt-resume.md` | v0.2.0 | implemented-tested |
| M2.3 DecisionRecord Schema 与迁移 | `src/scholartrace/schemas/decisions.py`, `src/scholartrace/persistence/models.py`, `src/scholartrace/persistence/migrations/versions/0002_add_decision_records.py` | `tests/integration/test_m2_decision_record.py`, `tests/integration/test_project_repository.py`, `docs/verification/m2-decision-record.md` | v0.2.0 | implemented-tested |
| M2.3 五类审批路径 | `src/scholartrace/graphs/research_question_decision.py` | `tests/integration/test_m2_decision_graph.py`, `docs/verification/m2-decision-record.md` | v0.2.0 | implemented-tested |
| M2.4 研究问题冻结与父版本 | `src/scholartrace/persistence/migrations/versions/0003_add_research_question_lifecycle.py`, `src/scholartrace/persistence/repository.py`, `src/scholartrace/graphs/research_question_decision.py` | `tests/integration/test_project_repository.py`, `tests/integration/test_m2_decision_graph.py`, `docs/verification/m2-versioning.md` | v0.2.0 | implemented-tested |
| M2.5 Checkpoint History、回滚与审计 | `src/scholartrace/graphs/research_question_decision.py`, `src/scholartrace/persistence/repository.py`, `src/scholartrace/schemas/decisions.py` | `tests/integration/test_m2_decision_graph.py`, `docs/verification/m2-history-rollback.md` | v0.2.0 | implemented-tested |
| M2 v0.2.0 发布候选 | `pyproject.toml`, `README.md`, `CHANGELOG.md` | `docs/verification/m2-release-candidate.md`, `scripts/check.py` | v0.2.0 | release-candidate |
| M3.1 独立文献目录 | `src/scholartrace/schemas/literature.py`, `src/scholartrace/persistence/literature_repository.py`, `src/scholartrace/persistence/migrations/versions/0004_add_literature_catalog.py` | `tests/integration/test_literature_repository.py`, `docs/verification/m3-catalog.md` | v0.3.0 | implemented-tested |
| M3.2 PDF 入库与质量标记 | `src/scholartrace/literature/ingestion.py`, `pyproject.toml` | `tests/integration/test_literature_ingestion.py`, `docs/verification/m3-pdf-ingestion.md` | v0.3.0 | implemented-tested |
| M3.3 Crossref/OpenAlex 元数据 | `src/scholartrace/literature/providers.py` | `tests/integration/test_literature_providers.py`, `docs/verification/m3-metadata-providers.md` | v0.3.0 | implemented-tested |
| M3 v0.3.0 发布候选 | `pyproject.toml`, `README.md`, `CHANGELOG.md` | `docs/verification/m3-release-candidate.md`, `scripts/check.py` | v0.3.0 | release-candidate |
| M4.1 项目文献审核与相关度 | `src/scholartrace/persistence/literature_repository.py`, `src/scholartrace/literature_relevance.py`, `src/scholartrace/persistence/migrations/versions/0005_add_project_document_review.py` | `tests/integration/test_m4_project_document_review.py`, `docs/verification/m4-project-review.md` | v0.4.0 | implemented-tested |
| M4.2 Chunk 与混合检索 | `src/scholartrace/schemas/literature.py`, `src/scholartrace/literature/chunking.py`, `src/scholartrace/literature/retrieval.py`, `src/scholartrace/persistence/literature_repository.py`, `src/scholartrace/persistence/migrations/versions/0006_add_document_chunks.py` | `tests/integration/test_m4_chunk_retrieval.py`, `docs/verification/m4-chunk-retrieval.md` | v0.4.0 | implemented-tested |
| M4.3 EvidenceCard 与引用校验 | `src/scholartrace/schemas/literature.py`, `src/scholartrace/literature/evidence.py`, `src/scholartrace/persistence/evidence_repository.py`, `src/scholartrace/persistence/migrations/versions/0007_add_evidence_cards.py` | `tests/integration/test_m4_evidence_cards.py`, `tests/fixtures/retrieval/m4-regression.json`, `docs/verification/m4-evidence-cards.md` | v0.4.0 | implemented-tested |
| M4 v0.4.0 发布候选 | `pyproject.toml`, `README.md`, `CHANGELOG.md`, `uv.lock` | `docs/verification/m4-release-candidate.md`, `scripts/check.py`, 独立 wheel/CLI/迁移 | v0.4.0 | release-candidate |
