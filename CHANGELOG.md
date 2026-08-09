# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 的结构，并使用语义化版本。

## [Unreleased]

### Added

- 严格校验的 `ResearchQuestion` 和轻量 `ResearchProjectState` 契约。
- 支持消息合并和有序去重的幂等 Reducer。
- 基于 SQLite、SQLAlchemy 与 Alembic 的 Project Repository 和可回滚初始迁移。
- 项目身份冲突、持久化重开、研究问题版本与跨项目隔离测试。
- `START → intake → build_research_question → save → END` 最小 LangGraph 与 SQLite Checkpointer。
- `scholartrace project create/continue/show` CLI、稳定 JSON 输出和明确错误退出码。

## [0.0.1] - 2026-08-09

### Added

- M0 可安装 Python 包骨架、uv 锁文件、pytest 和 Ruff 配置。
- 项目治理、长期进度、追溯、ADR 与验证记录骨架。
- 三个合成、脱敏的农业视觉项目 Fixture 及确定性校验。
- GitHub Actions 质量门禁和 Apache License 2.0。

此版本不包含 LangGraph、RAG、实验、论文或部署能力。
