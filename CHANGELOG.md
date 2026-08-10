# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 的结构，并使用语义化版本。

## [Unreleased]

后续变更将在下一版本记录。

### Added

- M9.1 版本化 `FigureSpec`、输入点契约、Artifact Bundle 元数据，以及只允许 verified/final `MetricResult` 的图表数据门禁。
- M9.2 批准 FigureSpec 的 CSV、可重建 `generate_figure.py`、PNG/SVG/PDF、Caption 和 provenance Bundle。
- M9.3 verified-only 图表建议、来源型 Caption、MetricResult 数值一致性和 provenance hash 检查。
- M9.4 完成 PNG/SVG/PDF 实际视觉验收、独立发布候选检查，并发布 `v0.9.0`。

### Boundary

- 图表输入仍必须来自 verified/final `MetricResult`；当前 Bundle 使用合成/脱敏农业视觉指标，不能当作真实科研结果。

## [0.9.0] - 2026-08-11

### Added

- M9 结果图表系统：版本化 `FigureSpec`、确定性 CSV 和 `generate_figure.py`、PNG/SVG/PDF 输出、来源型 Caption、数据/脚本 SHA-256 provenance 以及 MetricResult 数值一致性校验。
- 发布候选和视觉验收记录，明确区分图表文件可重建性、视觉检查与真实场景证据。

### Boundary

- M9 图表使用合成/脱敏指标完成离线验收；未证明真实农业视觉实验、论文结论或部署结果。

## [0.8.0] - 2026-08-11

### Added

- M8.1 绑定 frozen `ExperimentPlan` 的受控执行契约、资源上限和 0014 `controlled_runs` 迁移。
- argv 命令白名单、shell 注入拒绝、相对路径隔离和 Docker 无网络/只读工作区命令构造。
- M8.2 异步本地 Runner、取消/超时/日志上限、追加式 Run 事件和成功后的原子 staging Artifact 发布。
- M8.3 DebugCase 证据链、确定性诊断假设、人工修复审批、隔离修复工作区和回归门禁。
- M8.4.1 可替换的 JSON 离线追踪、MLflow 可选适配和 DVC manifest SHA-256 校验。

### Boundary

- M8.4.1 的 MLflow 结果会明确区分 recorded/unavailable/failed；当前环境未安装 MLflow，未宣称在线 tracking 成功。Docker 和真实农业视觉实验仍未验证。

## [0.7.0] - 2026-08-11

### Added

- M7.1 冻结门控的 `ExperimentPlan` 与实验矩阵，绑定数据版本、代码 SHA、环境锁、种子、基线和消融。
- M7.2 Run Manifest 导入、相对 Artifact 路径安全、缺失 provenance 的 `incomplete` 状态，以及报告指标的 `unverifiable` 边界。
- M7.3 独立 accuracy/MAE/RMSE 重算、verified/final 指标聚合和 Claim `insufficient` 降级。

### Boundary

- M7 不执行训练，不把日志临时值当作最终指标；受控 Runner、排错和真实场景验证留在后续里程碑。

## [0.6.0] - 2026-08-11

### Added

- M6.1 版本化 `AlgorithmSpec` / `PriorArtMap`、EvidenceCard 绑定和先验工作审批门禁。
- M6.2 `InnovationCandidate`、方法差异表和确定性完整度排序。
- M6.3 证伪计划、基线/消融要求，以及只允许进入验证的 `approved_for_experiment` 状态门禁。

### Boundary

- M6 不生成实验指标或“已证明创新”结论；候选必须在后续 M7 通过可追溯实验验证。

## [0.5.0] - 2026-08-11

### Added

- M5.1 版本化 `PipelineSpec` / `DataCollectionProtocol` 契约、内容哈希和人工批准门禁。
- M5.2 研究设计 Subgraph、人工 interrupt/resume、设计 DecisionRecord 审计和确定性 Mermaid 流程图。
- M5.3 管线连通性、数据划分泄漏检查、版本差异报告和批准前质量门禁。
- M5.4 仅批准方案可用的 Markdown/YAML 导出和确定性比较报告。

## [0.4.0] - 2026-08-11

### Added

- M4.1 项目文献 `candidate` / `approved` / `rejected` 状态、确定性相关度和人工审核元数据。
- M4.2 可追溯 `DocumentChunk`、BM25 + Vector 混合检索和索引失败时的旧快照保留。
- M4.3 经过来源片段与引用 locator 校验的 EvidenceCard，以及 10 条离线检索回归用例。

## [0.3.0] - 2026-08-11

### Added

- M3.1 独立文献目录的 `Document` / `ProjectDocument` Schema、0004 迁移和 SHA-256 去重。
- 项目与文献的候选关联和目录级元数据搜索；失败文献不会进入可检索结果。
- M3.2 合法 PDF 入库、pypdf 元数据/文本解析、运行时只读文件和解析质量标记。
- M3.3 可替换的 Crossref/OpenAlex 元数据客户端、来源标记和离线失败降级。

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
