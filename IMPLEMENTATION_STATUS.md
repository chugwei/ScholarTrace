# ScholarTrace 实施状态

- 项目状态：M4 已发布，M5 进行中
- 当前里程碑：M5 — 管线与数据采集设计
- 当前版本：`v0.4.0`
- 当前分支：`main`
- 远端：<https://github.com/chugwei/ScholarTrace.git>
- 更新时间：2026-08-11（Asia/Shanghai）

## 已完成

- 初始化独立仓库并配置 `main` 与 `origin`。
- 建立 Python 3.12、uv、src layout、pytest 与 Ruff 工程骨架。
- 完成产品范围、非目标、科研真实性、风险、ADR 和贡献规范。
- 建立三个农业视觉合成/脱敏 Fixture 及严格 Schema 校验。
- 建立本地统一质量门禁和最小权限 GitHub Actions workflow。
- GitHub Actions quality Run #1 在 `main` 上通过。
- 项目采用 Apache License 2.0，包元数据和 wheel 许可证文件已验证。
- `v0.0.1` annotated Tag 已推送并指向 M0 发布提交。
- 完成 Git archive 独立源码安装、sdist/wheel 构建与全新 venv 安装验收。
- 实际运行 Python 3.12 与 `actionlint` 容器。

## M0 小任务

- [x] M0.1 仓库与可安装 Python 骨架
- [x] M0.2 范围、非目标、风险、真实性与开发约定
- [x] M0.3 农业视觉黄金场景、3 个脱敏 Fixture 及校验
- [x] M0.4 Ruff、pytest、CI 与降级测试
- [x] M0.5 全新环境验收、工程记录、追溯矩阵和独立审查
- [x] M0.6 发布候选 CI 通过，`v0.0.1` Tag 已推送并核验

## M1 小任务

- [x] M1.1 ResearchProjectState、ResearchQuestion 与 Reducer 契约
- [x] M1.2 SQLite Project Repository、迁移与幂等写入
- [x] M1.3 `START → intake → build_research_question → save → END` 与 SQLite Checkpointer
- [x] M1.4 CLI 创建、继续和查看项目
- [x] M1.5 重启恢复、项目隔离、幂等与农业视觉黄金场景验收
- [x] M1.6 独立审查、合并 `main` 与 `v0.1.0` 发布

## M2 小任务

- [x] M2.1 缺失信息路由与 Conditional Edge
- [x] M2.2 `interrupt()` / `Command(resume=...)` 的暂停恢复契约
- [x] M2.3 批准、拒绝、修改、取消和暂停 DecisionRecord
- [x] M2.4 研究问题冻结与新版本创建
- [x] M2.5 Checkpoint History、回滚和审计查询
- [x] M2.6 独立审查、合并 `main` 与 `v0.2.0` 发布

## M3 小任务

- [x] M3.1 Document/ProjectDocument Schema、0004 迁移、SHA-256 去重和目录搜索
- [x] M3.2 合法 PDF 入库、原文只读保存、元数据解析和质量标记
- [x] M3.3 Crossref/OpenAlex 查询、失败降级和来源标记
- [x] M3.4 独立审查、合并 `main` 与 `v0.3.0` 发布

## M4 小任务

- [x] M4.1 项目文献 `candidate/approved/rejected`、确定性相关度与人工审核门禁
- [x] M4.2 Chunk/全文索引、BM25 + Vector 兼容检索与旧索引保留
- [x] M4.3 EvidenceCard、来源片段校验与固定检索回归集
- [x] M4.4 独立审查、合并 `main` 与 `v0.4.0` 发布

## M5 小任务

- [ ] M5.1 PipelineSpec/DataCollectionProtocol 契约与迁移（当前）
- [ ] M5.2 研究设计 Subgraph 与流程图
- [ ] M5.3 数据质量/泄漏检查与方案比较
- [ ] M5.4 Markdown/YAML 导出、独立审查、合并 `main` 与 `v0.5.0` 发布

## 当前验证

| 命令 | 结果 |
|---|---|
| `uv sync --all-groups` | 通过，CPython 3.12.13 |
| `uv run ruff format --check src tests scripts` | 通过 |
| `uv run ruff check src tests scripts` | 通过 |
| `uv run pytest` | 通过，75 passed |
| `uv run python scripts/validate_fixtures.py` | 通过，3 个合成 Fixture |
| `uv run python scripts/check.py` | 通过，75 passed |
| M1.1 State/Schema/Reducer 目标测试 | 通过，16 passed |
| M1.1 后全量 pytest | 通过，25 passed |
| M1.2 Repository/迁移集成测试 | 通过，12 passed |
| M1.2 后全量 pytest | 通过，37 passed |
| M1.3 Graph/Checkpointer 集成测试 | 通过，5 passed |
| M1.3 后全量 pytest | 通过，42 passed |
| M1.4 CLI 集成测试 | 通过，4 passed |
| M1.4 后全量 pytest | 通过，46 passed |
| `uv run scholartrace --help` | 通过，Windows UTF-8 中文显示正常 |
| M1.5 独立进程恢复 E2E | 通过，4 passed；参数化恢复 3/3 |
| M1.5 后全量 pytest | 通过，50 passed |
| `git archive 52bf99f` 独立源码验收 | 通过，50 passed，sdist/wheel 0.1.0 |
| 独立 wheel 安装、迁移、CLI 恢复 | 通过，版本 0.1.0，Apache-2.0 |
| M1 发布候选秘密/大文件/内部路径扫描 | 通过，均为 0 |
| `actionlint` Docker | 通过，无诊断 |
| GitHub Actions quality Run #14 | 通过，commit `52bf99f` |
| GitHub Actions quality Run #16 | 通过，merge commit `986eee3` |
| `v0.1.0` annotated Tag | 远端对象 `a7ef171`，peeled commit `986eee3` |
| M2.1 Conditional Edge 集成测试 | 通过，8 passed |
| M2.1 后全量 pytest | 通过，58 passed |
| M2.2 interrupt/resume 集成测试 | 通过，4 passed |
| M2.2 后全量 pytest | 通过，62 passed |
| Git archive 全新环境安装与门禁 | 通过，8 passed |
| `uv build` + 全新 venv wheel 安装/import | 通过，版本 0.1.0 |
| `docker run --rm python:3.12-slim python --version` | 通过，Python 3.12.13 |
| `actionlint` Docker 静态检查 | 通过，无诊断输出 |
| GitHub Actions quality Run #4 | 通过，commit `42238c1`，10s |
| `git ls-remote origin refs/heads/main` | 本地与远端 `main` 同步 |
| Apache-2.0 官方正文比对 | 通过 |
| 安装包 `License-Expression` | `Apache-2.0` |
| wheel 许可证文件 | 包含 `dist-info/licenses/LICENSE` |
| `v0.0.1^{}` | `42238c1072675763d59a3c6455896eaa289f6b1a` |
| M2.3 DecisionRecord/审批图目标测试 | 通过，11 passed |
| M2.3 后全量 pytest | 通过，73 passed |
| M2.3 迁移 `0002 → 0001 → base → head` | 通过，DecisionRecord 表正确移除并恢复 |
| M2.3 Ruff format/lint | 通过，38 files formatted、无诊断 |
| M2.3 提交与远端 Ref | `b467522`；`origin/feat/m2-human-approval` 已核验同步 |
| M2.3 GitHub Actions | 未验证：当前环境访问 GitHub Actions API 发生 SSL 连接错误 |
| M2.4 生命周期/版本目标测试 | 通过，29 passed |
| M2.4 后全量质量门禁 | 通过，75 passed；Ruff 39 files formatted；3 个 Fixture |
| M2.4 迁移 `0003 → 0002 → 0001 → base → head` | 通过，生命周期列正确移除并恢复 |
| M2.5 History/rollback 目标测试 | 通过，13 passed |
| M2.5 后全量质量门禁 | 通过，76 passed；Ruff 39 files formatted；3 个 Fixture |
| M2.6 发布候选全量质量门禁 | 通过，76 passed；Ruff 39 files formatted；3 个 Fixture |
| `uv build` v0.2.0 | 通过，sdist/wheel 构建成功 |
| 独立 wheel venv 安装/import/CLI/迁移 | 通过，版本 0.2.0，迁移 0003 |
| `actionlint` Docker | 通过，无诊断 |
| 发布候选秘密/个人路径/大文件扫描 | 通过，0 matches、tracked >5MB 为 0 |
| M2 main 合并 | 通过，merge commit `6689572`，main smoke test 与全量门禁通过 |
| `v0.2.0` annotated Tag | 通过，tag object `f4990a7d`，peeled commit `6689572`，远端已核验 |
| M3.1 文献目录目标测试 | 通过，3 passed |
| M3.1 Ruff format/lint | 通过，46 files formatted、无诊断 |
| M3.2 PDF 入库目标测试 | 通过，3 passed |
| M3.2 后全量质量门禁 | 通过，82 passed；Ruff 46 files formatted；3 个 Fixture |
| M3.3 元数据客户端目标测试 | 通过，4 passed；MockTransport 离线 |
| M3.3 后全量质量门禁 | 通过，86 passed；Ruff 48 files formatted；3 个 Fixture |
| `uv build` v0.3.0 | 通过，sdist/wheel 构建成功 |
| 独立 wheel venv 安装/import/CLI/迁移 | 通过，版本 0.3.0，迁移 0004 |
| M3 main 合并 | 通过，merge commit `c12b362`，main smoke test 与全量门禁通过 |
| `v0.3.0` annotated Tag | 通过，tag object `8ac3d022`，peeled commit `c12b362`，远端已核验 |
| M4.1 项目文献审核目标测试 | 通过，3 passed；迁移升级/回滚、相关度排序、审核与失败文献门禁 |
| M4.1 Ruff format/lint | 通过，49 files unchanged；All checks passed |
| M4.1 全量质量门禁 | 通过，`scripts/check.py`；89 passed；3 个合成 Fixture |
| M4.2 Chunk/检索目标测试 | 通过，4 passed；0006 迁移、偏移回切、approved 隔离、混合检索和失败重建保留 |
| M4.2 全量质量门禁 | 通过，`scripts/check.py`；93 passed；3 个合成 Fixture |
| M4.3 EvidenceCard/回归目标测试 | 通过，5 passed；0007 迁移、approved 门禁、locator/片段校验、幂等和 10 条回归 |
| M4.3 全量质量门禁 | 通过，`scripts/check.py`；98 passed；3 个合成 Fixture |
| M4.4 发布候选全量门禁 | 通过，98 passed；v0.4.0 wheel、独立 venv、CLI、迁移 0007、actionlint 和许可证检查通过 |
| M4 main 合并与发布 | 通过，merge `a193291`；main smoke/全量 98 passed；Tag object `11593b0`，peeled `a193291` |

## 当前限制

- M1 已完成并发布；依赖漏洞服务因 PyPI 网络超时未验证，不能视为漏洞扫描通过。
- M2.1–M2.6 已完成缺失信息路由、真实 interrupt/resume、DecisionRecord、五类审批、研究问题版本冻结、受控 checkpoint 回滚和 `v0.2.0` 发布；CI API 读取与依赖审计仍有明确限制。
- M3.1–M3.4 已完成独立文献目录、项目 candidate 关联、SHA-256 去重、合法 PDF 解析、只读运行时保存、Crossref/OpenAlex 归一化、显式失败降级和 `v0.3.0` 发布；M4.1–M4.3 已实现项目审核、Chunk、可替换混合检索、EvidenceCard 和离线回归，但 M4.4 发布审查仍未完成。
- RAG、实验、论文、Web 和部署能力仍未实现。

## 下一步

下一步进入 M5.1：冻结 PipelineSpec/DataCollectionProtocol 契约并设计兼容迁移；不把 M4 的离线回归或合成文献结果宣传为真实场景证据。
