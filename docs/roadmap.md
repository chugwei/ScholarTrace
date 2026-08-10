# 发布路线

ScholarTrace 按可验收版本逐步建设。版本只有在代码、测试、文档、兼容性和发布证据完整时才进入下一阶段。

## 里程碑总表

| 里程碑 | 版本 | 状态 | 分支 | Tag | 验证 |
|---|---|---|---|---|---|
| M0 仓库骨架 | v0.0.1 | completed | main | [v0.0.1](https://github.com/chugwei/ScholarTrace/tree/v0.0.1) | 本地、独立环境、CI 通过 |
| M1 持久化项目图 | v0.1.0 | completed | feat/m1-project-state | [v0.1.0](https://github.com/chugwei/ScholarTrace/tree/v0.1.0) | main CI、独立源码/wheel、E2E 通过 |
| M2 人工审批与历史 | v0.2.0 | in_progress | feat/m2-human-approval | — | 任务拆分完成 |
| M3 独立文献库 | v0.3.0 | pending | feat/m3-literature-library | — | — |
| M4 可信证据 RAG | v0.4.0 | pending | feat/m4-evidence-rag | — | — |
| M5 管线与数据设计 | v0.5.0 | pending | feat/m5-pipeline-data-design | — | — |
| M6 算法与创新候选 | v0.6.0 | pending | feat/m6-algorithm-innovation | — | — |
| M7 实验注册与导入 | v0.7.0 | pending | feat/m7-experiment-registry | — | — |
| M8 Runner 与排错 | v0.8.0 | pending | feat/m8-runner-debugging | — | — |
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
| M2.3 | 审批 DecisionRecord | 批准/拒绝/修改/取消/暂停路径测试 | in_progress |
| M2.4 | 研究问题版本 | 冻结、新版本和内容哈希测试 | pending |
| M2.5 | 历史与回滚 | Checkpoint History、回滚、审计测试 | pending |
| M2.6 | M2 发布 | 独立审查、main CI、`v0.2.0` | pending |
