# ScholarTrace 实施状态

- 项目状态：M1 已发布，进入 M2
- 当前里程碑：M2 — 人工澄清、审批与版本历史
- 当前版本：`v0.1.0`
- 当前分支：`main`
- 远端：<https://github.com/chugwei/ScholarTrace.git>
- 更新时间：2026-08-10（Asia/Shanghai）

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

- [ ] M2.1 缺失信息路由与 Conditional Edge
- [ ] M2.2 `interrupt()` / `Command(resume=...)` 的暂停恢复契约
- [ ] M2.3 批准、拒绝、修改、取消和暂停 DecisionRecord
- [ ] M2.4 研究问题冻结与新版本创建
- [ ] M2.5 Checkpoint History、回滚和审计查询
- [ ] M2.6 独立审查、合并 `main` 与 `v0.2.0` 发布（当前）

## 当前验证

| 命令 | 结果 |
|---|---|
| `uv sync --all-groups` | 通过，CPython 3.12.13 |
| `uv run ruff format --check src tests scripts` | 通过 |
| `uv run ruff check src tests scripts` | 通过 |
| `uv run pytest` | 通过，50 passed |
| `uv run python scripts/validate_fixtures.py` | 通过，3 个合成 Fixture |
| `uv run python scripts/check.py` | 通过，50 passed |
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

## 当前限制

- M1 已完成并发布；依赖漏洞服务因 PyPI 网络超时未验证，不能视为漏洞扫描通过。
- M2 及 RAG、实验、论文、Web 和部署能力仍未实现。

## 下一步

从 M2.1 开始：先为缺失信息路由、人工暂停/恢复和 DecisionRecord 写失败测试，再实现审批与版本历史。
