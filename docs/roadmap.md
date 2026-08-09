# 发布路线

ScholarTrace 按可验收版本逐步建设。版本只有在代码、测试、文档、兼容性和发布证据完整时才进入下一阶段。

## 里程碑总表

| 里程碑 | 版本 | 状态 | 分支 | Tag | 验证 |
|---|---|---|---|---|---|
| M0 仓库骨架 | v0.0.1 | in_progress | main | 未创建 | 本地与 CI 通过，等待 LICENSE |
| M1 持久化项目图 | v0.1.0 | pending | feat/m1-project-state | — | — |
| M2 人工审批与历史 | v0.2.0 | pending | feat/m2-human-approval | — | — |
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
| M0.6 | M0 发布 | LICENSE 已确认，main 同步，v0.0.1 Tag 推送 | blocked |

## 当前发布阻塞

1. 许可证类型尚未确认。
恢复顺序：确认许可证、添加 `LICENSE`、重跑完整门禁，再创建版本 Tag。
