# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 的结构，并使用语义化版本。

## [Unreleased]

后续变更将在下一版本记录。

### Added

- M3.1 独立文献目录的 `Document` / `ProjectDocument` Schema、0004 迁移和 SHA-256 去重。
- 项目与文献的候选关联和目录级元数据搜索；失败文献不会进入可检索结果。

## [0.2.0] - 2026-08-10

### Added

- M2.1 研究问题缺失信息检测与 Conditional Edge 路由。
- 不完整研究问题停在 `awaiting_clarification`，不会写入正式实体。
- M2.2 基于 SQLite Checkpoint 的 `interrupt()` / `Command(resume=...)` 暂停恢复。
- M2.3 DecisionRecord Schema、SQLite 迁移和幂等审计记录。
- 研究问题审批图支持批准、拒绝、修改、取消和暂停，并保留同一 thread 的恢复边界。
- M2.4 研究问题 `draft/frozen` 生命周期、冻结元数据和父版本追溯。
- 冻结版本不能被隐式覆盖；修改必须创建新的可审批版本。
- M2.5 提供 thread 级 Checkpoint History、受控回滚和 `rolled_back` 审计记录。

## [0.1.0] - 2026-08-09

### Added

- 严格校验的 `ResearchQuestion` 和轻量 `ResearchProjectState` 契约。
- 支持消息合并和有序去重的幂等 Reducer。
- 基于 SQLite、SQLAlchemy 与 Alembic 的 Project Repository 和可回滚初始迁移。
- 项目身份冲突、持久化重开、研究问题版本与跨项目隔离测试。
- `START → intake → build_research_question → save → END` 最小 LangGraph 与 SQLite Checkpointer。
- `scholartrace project create/continue/show` CLI、稳定 JSON 输出和明确错误退出码。
- 三进程恢复、重放幂等和跨项目隔离的农业视觉黄金场景 E2E。

## [0.0.1] - 2026-08-09

### Added

- M0 可安装 Python 包骨架、uv 锁文件、pytest 和 Ruff 配置。
- 项目治理、长期进度、追溯、ADR 与验证记录骨架。
- 三个合成、脱敏的农业视觉项目 Fixture 及确定性校验。
- GitHub Actions 质量门禁和 Apache License 2.0。

此版本不包含 LangGraph、RAG、实验、论文或部署能力。
