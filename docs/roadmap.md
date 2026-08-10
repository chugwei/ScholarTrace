# 发布路线

ScholarTrace 按可验收版本逐步建设。版本只有在代码、测试、文档、兼容性和发布证据完整时才进入下一阶段。

## 里程碑总表

| 里程碑 | 版本 | 状态 | 分支 | Tag | 验证 |
|---|---|---|---|---|---|
| M0 仓库骨架 | v0.0.1 | completed | main | [v0.0.1](https://github.com/chugwei/ScholarTrace/tree/v0.0.1) | 本地、独立环境、CI 通过 |
| M1 持久化项目图 | v0.1.0 | completed | feat/m1-project-state | [v0.1.0](https://github.com/chugwei/ScholarTrace/tree/v0.1.0) | main CI、独立源码/wheel、E2E 通过 |
| M2 人工审批与历史 | v0.2.0 | completed | main | [v0.2.0](https://github.com/chugwei/ScholarTrace/tree/v0.2.0) | merge `6689572`、main 门禁、Tag 已核验 |
| M3 独立文献库 | v0.3.0 | completed | main | [v0.3.0](https://github.com/chugwei/ScholarTrace/tree/v0.3.0) | merge `c12b362`、main 门禁、Tag 已核验 |
| M4 可信证据 RAG | v0.4.0 | completed | main | [v0.4.0](https://github.com/chugwei/ScholarTrace/tree/v0.4.0) | merge `a193291`、main 门禁、Tag 已核验 |
| M5 管线与数据设计 | v0.5.0 | completed | main | [v0.5.0](https://github.com/chugwei/ScholarTrace/tree/v0.5.0) | merge `9aef2d8`、main 门禁、Tag 已核验 |
| M6 算法与创新候选 | v0.6.0 | completed | main | [v0.6.0](https://github.com/chugwei/ScholarTrace/tree/v0.6.0) | merge `0161739`、main 门禁、Tag 已核验 |
| M7 实验注册与导入 | v0.7.0 | completed | main | [v0.7.0](https://github.com/chugwei/ScholarTrace/tree/v0.7.0) | merge `1cd9280`、main 门禁、Tag 已核验 |
| M8 Runner 与排错 | v0.8.0 | pending | feat/m8-runner-debugging | — | M7 已发布，入口待打开 |
| M9 图表系统 | v0.9.0 | pending | feat/m9-figures | — | — |
| M10 论文与引用 | v0.10.0 | pending | feat/m10-manuscript | — | — |
| M11 Web 工作台 | v0.11.0 | pending | feat/m11-web-workbench | — | — |
| M12 交付与部署 | v1.0.0 | pending | feat/m12-deployment | — | — |

## M0 验收进度

| ID | 任务 | 验收标准 | 状态 |
|---|---|---|---|
| M0.1 | 仓库与 Python 骨架 | Python 3.12 安装、导入、Ruff、pytest 通过 | completed |
| M0.2 | 工程规范与范围 | 范围、非目标、风险、真实性、ADR 和贡献规范完整 | completed |
| M0.3 | 黄金场景与 Fixture | 3 个脱敏 Fixture 通过确定性 Schema 校验 | completed |
| M0.4 | CI 与质量门禁 | 本地和 GitHub Actions 执行同一锁定检查 | completed |
| M0.5 | 独立验收 | 全新环境安装、构建、测试和审查记录通过 | completed |
| M0.6 | M0 发布 | LICENSE 已确认，main 同步，v0.0.1 Tag 推送 | completed |

## M1 入口

1. 创建 `feat/m1-project-state`；
2. 冻结 ResearchProjectState、ResearchQuestion 与 Repository 契约；
3. 先写恢复、隔离、Reducer 和幂等测试，再实现最小持久化 Graph；
4. 通过 M1 门禁后发布 `v0.1.0`。

## M1 验收批次

| ID | 批次 | 主要证据 | 状态 |
|---|---|---|---|
| M1.1 | State、ResearchQuestion、Reducer 契约 | Schema 单元测试、Reducer 重放测试 | completed |
| M1.2 | SQLite Project Repository | 迁移、事务、幂等与隔离测试 | completed |
| M1.3 | 最小 LangGraph + SQLite Checkpointer | Graph 集成测试、checkpoint 证据 | completed |
| M1.4 | CLI create/continue/show | CLI 集成与错误路径测试 | completed |
| M1.5 | 重启恢复与黄金样例 | 独立进程恢复成功率 100%、项目泄漏 0 | completed |
| M1.6 | M1 发布 | 独立审查、main CI、`v0.1.0` | completed |

## M2 验收批次

| ID | 批次 | 主要证据 | 状态 |
|---|---|---|---|
| M2.1 | 缺失信息路由 | Conditional Edge 失败测试与农业视觉样例 | completed |
| M2.2 | 暂停与恢复 | `interrupt()`、`Command(resume=...)` 集成测试 | completed |
| M2.3 | 审批 DecisionRecord | 批准/拒绝/修改/取消/暂停路径测试 | completed |
| M2.4 | 研究问题版本 | 冻结、新版本和内容哈希测试 | completed |
| M2.5 | 历史与回滚 | Checkpoint History、回滚、审计测试 | completed |
| M2.6 | M2 发布 | 独立审查、main CI、`v0.2.0` | completed |

## M3 验收批次

| ID | 批次 | 主要证据 | 状态 |
|---|---|---|---|
| M3.1 | Document/ProjectDocument 与 SHA-256 目录 | 迁移、去重、项目候选关联和目录搜索测试 | completed |
| M3.2 | 合法 PDF 入库与质量标记 | 运行时只读保存、解析失败降级和重复文件测试 | completed |
| M3.3 | Crossref/OpenAlex 与离线降级 | MockTransport、来源标记和网络失败测试 | completed |
| M3.4 | M3 发布 | 独立审查、main CI、`v0.3.0` | completed |

## M4 验收批次

| ID | 批次 | 主要证据 | 状态 |
|---|---|---|---|
| M4.1 | candidate/approved/rejected 与相关度 | 0005 迁移、相关度排序、人工审批和失败文献门禁 | completed |
| M4.2 | Chunk/全文索引与混合检索 | 0006 迁移、偏移回切、BM25/Vector 兼容检索和旧索引保留 | completed |
| M4.3 | EvidenceCard 与检索回归 | DOI/URL/片段校验、固定 10 条回归集 | completed |
| M4.4 | M4 发布 | 独立审查、main CI、`v0.4.0` | completed |

## M5 验收批次

| ID | 批次 | 主要证据 | 状态 |
|---|---|---|---|
| M5.1 | PipelineSpec/DataCollectionProtocol 契约与迁移 | Schema、兼容迁移和黄金样例 | completed |
| M5.2 | 研究设计 Subgraph 与流程图 | 节点、版本和人工批准边界测试 | completed |
| M5.3 | 数据质量/泄漏检查与方案比较 | 失败路径、版本对比和安全检查 | completed |
| M5.4 | Markdown/YAML 导出与 M5 发布 | 独立审查、main CI、`v0.5.0` | completed |

## M6 验收批次

| ID | 批次 | 主要证据 | 状态 |
|---|---|---|---|
| M6.1 | AlgorithmSpec/Prior Art Map 契约与迁移 | 0009、证据绑定、版本和审批顺序测试 | completed |
| M6.2 | InnovationCandidate 与方法差异 | 候选结构、差异表和确定性排序测试 | completed |
| M6.3 | 证伪、基线/消融与状态门禁 | 审批阻断、实验入口和真实性测试 | completed |
| M6.4 | M6 发布 | 独立审查、main CI、`v0.6.0` | completed |

## M7 验收批次

| ID | 批次 | 主要证据 | 状态 |
|---|---|---|---|
| M7.1 | ExperimentPlan、实验矩阵和冻结门禁 | 0011、版本/审批/回滚测试 | completed |
| M7.2 | Run Manifest 与现有产物导入 | 缺失证据、不完整状态和导入隔离测试 | completed |
| M7.3 | 指标独立重算、统计汇总和 Claim 更新 | 重算一致性、汇总和 Claim 门禁测试 | completed |
| M7.4 | M7 发布 | 独立审查、main CI、`v0.7.0` | completed |
