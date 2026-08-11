# ScholarTrace 实施状态

- 项目状态：M11.4 进行中
- 当前里程碑：M11 — FastAPI、SSE 与 Web 工作台
- 当前版本：`v0.10.0`
- 当前分支：`feat/m11-web-workbench`
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

- [x] M5.1 PipelineSpec/DataCollectionProtocol 契约与迁移
- [x] M5.2 研究设计 Subgraph 与流程图
- [x] M5.3 数据质量/泄漏检查与方案比较
- [x] M5.4 Markdown/YAML 导出
- [x] M5.4 独立审查、合并 `main` 与 `v0.5.0` 发布

## M6 小任务

- [x] M6.1 AlgorithmSpec/Prior Art Map 契约与迁移
- [x] M6.2 InnovationCandidate、差异表和机制假设
- [x] M6.3 证伪实验、基线/消融建议和创新状态门禁
- [x] M6.4 独立审查、合并 `main` 与 `v0.6.0` 发布

## M7 小任务

- [x] M7.1 ExperimentPlan、实验矩阵和冻结门禁
- [x] M7.2 Run Manifest、现有产物导入和不可验证状态
- [x] M7.3 指标独立重算、统计汇总和 Claim 更新
- [x] M7.4 独立审查、合并 `main` 与 `v0.7.0` 发布

## M8 小任务

- [x] M8.1 受控执行契约、命令白名单、资源限制和 0014 迁移
- [x] M8.2 启动、取消、超时、流式日志和失败产物隔离
- [x] M8.3 DebugCase、诊断假设排序、安全修复分支和回归门禁
- [x] M8.4.1 JSON 离线追踪、MLflow 可选适配和 DVC manifest 校验
- [x] M8.4.2 独立审查与发布候选
- [x] M8.4.3 合并 `main`、推送 `v0.8.0` Tag 并关闭 M8

## M9 小任务

- [x] M9.1 FigureSpec、输入数据契约、Artifact 元数据和 0017 迁移
- [x] M9.2 确定性绘图脚本与 PNG/SVG/PDF 输出
- [x] M9.3 Caption、图表建议、数据/脚本溯源和数值一致性检查
- [x] M9.4 视觉验收、独立审查、合并 `main` 与 `v0.9.0` 发布

## M10 小任务

- [x] M10.1 Manuscript/Section Contract/Claim Ledger 契约与 0018 迁移
- [x] M10.2 章节生成、BibTeX 和引用解析
- [x] M10.3 章节一致性、证据缺口与数字回溯门禁
- [x] M10.4 独立审查、合并 `main` 与 `v0.10.0` 发布

## M11 小任务

- [x] M11.1 FastAPI Project/Run/Artifact API 与持久化读写
- [x] M11.2 SSE Run 时间线与连接降级
- [x] M11.3 Web 工作台页面、审批组件和黄金样例垂直流程
- [ ] M11.4 独立审查、合并 `main` 与 `v0.11.0` 发布

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
| M5.1 设计 Repository 目标测试 | 通过，4 passed；0008 迁移、版本幂等、批准/拒绝、父版本和项目隔离 |
| M5.1 全量质量门禁 | 通过，`scripts/check.py`；102 passed；3 个合成 Fixture |
| M5.2 Subgraph/流程图目标测试 | 通过，3 passed；interrupt/resume、批准/拒绝审计、未批准降级和 Mermaid 输出 |
| M5.2 全量质量门禁 | 通过，`scripts/check.py`；105 passed；3 个合成 Fixture |
| M5.3 质量/版本比较目标测试 | 通过，4 passed；管线连通性、泄漏控制、版本差异和批准阻断 |
| M5.3 全量质量门禁 | 通过，`scripts/check.py`；109 passed；3 个合成 Fixture |
| M5.4 导出目标测试 | 通过，2 passed；draft 阻断、approved Markdown/YAML 确定性输出和版本/SHA-256 保留 |
| M5.4 全量质量门禁 | 通过，`scripts/check.py`；111 passed；3 个合成 Fixture |
| M5 main 合并与发布 | 通过，merge `9aef2d8`；main smoke/全量 111 passed；Tag object `c35ed74`，peeled `9aef2d8` |
| M5 发布候选独立验收 | 通过，v0.5.0 wheel/sdist、独立 venv、PyYAML、CLI、迁移 0008、actionlint 和许可证检查通过 |
| M6.1 算法契约目标测试 | 通过，4 passed；0009 迁移升降级、证据绑定、审批顺序和项目隔离 |
| M6.1 全量质量门禁 | 通过，`scripts/check.py`；115 passed；3 个合成 Fixture |
| M6.2 候选目标测试 | 通过，6 passed；0010 迁移、引用一致性、版本父链和确定性排序 |
| M6.2 全量质量门禁 | 通过，`scripts/check.py`；117 passed；3 个合成 Fixture |
| M6.3 门禁目标测试 | 通过，8 passed；证伪提案、审批顺序、`not_novel` 阻断、撤回和拒绝 |
| M6.3 全量质量门禁 | 通过，`scripts/check.py`；119 passed；3 个合成 Fixture |
| M6.4 发布候选 | 通过，v0.6.0 wheel/sdist、隔离 venv、CLI、迁移 0010、actionlint、Apache-2.0、内部文件排除和秘密扫描；详见 `docs/verification/m6-release-candidate.md` |
| M6 main 合并与发布 | 通过，merge `0161739`；main smoke/全量 119 passed；Tag object `9bfc324`，peeled `0161739` |
| M7.1 实验计划目标测试 | 通过，3 passed；0011 迁移、批准算法、冻结、拒绝、幂等和父版本 |
| M7.1 全量质量门禁 | 通过，`scripts/check.py`；122 passed；3 个合成 Fixture |
| M7.2 Run/Metric 目标测试 | 通过，3 passed；0012 迁移、完整性、相对路径和不可验证指标门禁 |
| M7.2 全量质量门禁 | 通过，`scripts/check.py`；125 passed；3 个合成 Fixture |
| M7.3 指标/Claim 目标测试 | 通过，5 passed；独立重算、verified 聚合、数据版本和 Claim 降级 |
| M7.3 全量质量门禁 | 通过，`scripts/check.py`；127 passed；3 个合成 Fixture |
| M7.4 发布候选 | 通过，v0.7.0 wheel/sdist、隔离 venv、CLI、迁移 0013、actionlint、Apache-2.0、内部文件排除和秘密扫描；详见 `docs/verification/m7-release-candidate.md` |
| M7 main 合并与发布 | 通过，merge `1cd9280`；main smoke/全量 127 passed；Tag object `95af661`，peeled `1cd9280` |
| M8.1 受控 Runner 契约目标测试 | 通过，6 passed；0014 迁移升降级、冻结计划门禁、命令白名单、路径隔离和 Docker argv 构造 |
| M8.1 Ruff format/lint | 通过；95 files formatted/unchanged，All checks passed |
| M8.2 Runner 生命周期目标测试 | 通过，10 passed；成功发布、失败/取消/超时隔离、日志上限、事件顺序和 0015↔0014 回滚 |
| M8.2 全量质量门禁 | 通过，`scripts/check.py`；137 passed；3 个合成 Fixture |
| M8.3 DebugCase/修复回归目标测试 | 通过，13 passed；失败证据、确定性假设、审批门禁、隔离修复和真实回归命令 |
| M8.3 全量质量门禁 | 通过，`scripts/check.py`；140 passed；3 个合成 Fixture |
| M8.4.1 tracking/DVC 目标测试 | 通过，3 passed；JSON 追踪、MLflow 可用性降级、DVC hash/path 校验 |
| M8.4.1 全量质量门禁 | 通过，`scripts/check.py`；143 passed；3 个合成 Fixture |
| M8.4.2 发布候选独立验收 | 通过；v0.8.0 wheel/sdist、隔离 venv、迁移 0016、许可证、秘密/大文件扫描、Git archive 和 actionlint |
| M8.4.3 main 合并与 v0.8.0 发布 | 通过，merge `99f72e1`；main 143 passed；annotated Tag `v0.8.0` 已推送，peeled `99f72e1` |
| M9.1 FigureSpec/Repository 目标测试 | 通过，3 passed；0017 迁移回滚、内容哈希、verified MetricResult/data_version 门禁和审批 |
| M9.1 全量质量门禁 | 通过，`scripts/check.py`；146 passed；3 个合成 Fixture |
| M9.2 绘图 Artifact Bundle 目标测试 | 通过，5 passed；CSV/脚本/PNG/SVG/PDF/Caption/provenance 和删除后脚本重建 |
| M9.2 全量质量门禁 | 通过，`scripts/check.py`；148 passed；3 个合成 Fixture |
| M9.3 图表建议/Caption/数值目标测试 | 通过，6 passed；verified-only 建议、来源 Caption、CSV/MetricResult 和 provenance hash 检查 |
| M9.3 全量质量门禁 | 通过，`scripts/check.py`；149 passed；3 个合成 Fixture |
| M9.4 实际视觉验收 | 通过；PNG、SVG 和 PDF 已实际打开检查，未发现裁切、重叠、黑块或不可读标签；PDF 另经 Poppler 渲染检查 |
| M9.4 发布候选 | 通过；wheel/sdist、隔离 venv、0017 迁移、CLI、Apache-2.0、内部文件排除、秘密/大文件扫描和 actionlint |
| M9.4 main 合并与 v0.9.0 发布 | 通过；merge `4e60f48`；main 149 passed；annotated Tag `v0.9.0` object `0290f40` 已推送，peeled `4e60f48` |
| M10.1 契约/Repository 目标测试 | 通过，4 passed；0018 回滚、版本父链、项目隔离和 Claim evidence gate |
| M10.2 BibTeX/章节草稿目标测试 | 通过，5 passed；BibTeX 解析、引用缺失报告、SectionContract 草稿门禁 |
| M10.2 全量质量门禁 | 通过，`scripts/check.py`；158 passed；3 个合成 Fixture |
| M10.3 一致性目标测试 | 通过，4 passed；Claim/citation/MetricResult 显式标记、数字漂移和 Conclusion 新 Claim |
| M10.3 全量质量门禁 | 通过，`scripts/check.py`；162 passed；3 个合成 Fixture |
| M10.4 发布候选 | 通过；v0.10.0 wheel/sdist、独立 venv、0018 迁移、许可证、秘密/大文件扫描、Git archive、Docker actionlint 和 Python smoke |
| M10.4 main 合并与 v0.10.0 发布 | 通过；merge `33cf794`；main 162 passed；annotated Tag `v0.10.0` object `154fcbd` 已推送，peeled `33cf794` |
| M11.1 API 目标测试 | 通过，3 passed；Project/Run/Artifact 路由、Repository 复用和项目隔离 |
| M11.1 全量质量门禁 | 通过，`scripts/check.py`；165 passed；3 个合成 Fixture |
| M11.2 SSE 目标测试 | 通过，3 passed；有序事件、Last-Event-ID 重放、retry/keep-alive 和错误降级 |
| M11.2 全量质量门禁 | 通过，`scripts/check.py`；165 passed；3 个合成 Fixture |
| M11.3 API/E2E 目标测试 | 通过，4 passed；页面契约、四个 SectionContract、人工审阅状态和 SSE 路径 |
| M11.3 全量质量门禁 | 通过，`scripts/check.py`；166 passed；3 个合成 Fixture |
| M11.3 浏览器垂直验收 | 通过；URL 项目恢复、Run sequence 0–4 实时时间线、四章节草稿、`in_review` 人工审阅；详见 `docs/verification/m11-workbench.md` |

## 当前限制

- M1 已完成并发布；依赖漏洞服务因 PyPI 网络超时未验证，不能视为漏洞扫描通过。
- M2.1–M2.6 已完成缺失信息路由、真实 interrupt/resume、DecisionRecord、五类审批、研究问题版本冻结、受控 checkpoint 回滚和 `v0.2.0` 发布；CI API 读取与依赖审计仍有明确限制。
- M3.1–M3.4 已完成独立文献目录、项目 candidate 关联、SHA-256 去重、合法 PDF 解析、只读运行时保存、Crossref/OpenAlex 归一化、显式失败降级和 `v0.3.0` 发布；M4 已发布 v0.4.0；M5 已发布 v0.5.0，包含版本化设计契约、人工 Subgraph、流程图、质量/泄漏门禁、版本比较和批准方案导出。
- M6.1–M6.3 已实现 AlgorithmSpec/PriorArtMap、InnovationCandidate、方法差异、完整度排序、证伪提案和验证入口门禁；`approved_for_experiment` 仍不是创新结论。M7.1–M7.3 已实现计划冻结、Run/Metric 导入边界、独立重算、verified 聚合和 Claim 降级。M8 已发布 v0.8.0，包含 frozen plan 绑定、argv 安全策略、异步本地进程、取消/超时、日志事件、成功后 staging 发布、DebugCase 证据链、隔离回归、JSON/DVC 离线适配和 MLflow 可用性降级。M9 已发布 v0.9.0，完成 FigureSpec 门禁、可重建三格式 Bundle、verified-only 建议、来源 Caption、数值/provenance 检查和实际视觉验收；M10 已发布 v0.10.0，完成 Manuscript/SectionContract/Claim Ledger、离线 BibTeX、引用解析、章节一致性和显式数字回溯。M11.1–M11.3 已完成 API、SSE 和浏览器工作台验收；当前只证明合成/脱敏垂直演示，M11.4 发布审查、M12 部署和真实场景验证仍未完成。

## 下一步

下一步完成 M11.4 独立审查、发布候选、合并 `main` 和 `v0.11.0`；不把合成演示描述为真实场景交付。
