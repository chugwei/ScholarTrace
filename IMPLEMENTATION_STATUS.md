# ScholarTrace 实施状态

- 项目状态：M1 契约设计
- 当前里程碑：M1 — 最小持久化科研项目图
- 当前版本：`v0.0.1`
- 当前分支：`feat/m1-project-state`
- 远端：<https://github.com/chugwei/ScholarTrace.git>
- 更新时间：2026-08-09（Asia/Shanghai）

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

- [ ] M1.1 ResearchProjectState、ResearchQuestion 与 Reducer 契约（当前）
- [ ] M1.2 SQLite Project Repository、迁移与幂等写入
- [ ] M1.3 `START → intake → build_research_question → save → END` 与 SQLite Checkpointer
- [ ] M1.4 CLI 创建、继续和查看项目
- [ ] M1.5 重启恢复、项目隔离、幂等与农业视觉黄金场景验收
- [ ] M1.6 独立审查、合并 `main` 与 `v0.1.0` 发布

## 当前验证

| 命令 | 结果 |
|---|---|
| `uv sync --all-groups` | 通过，CPython 3.12.13 |
| `uv run ruff format --check src tests scripts` | 通过 |
| `uv run ruff check src tests scripts` | 通过 |
| `uv run pytest` | 通过，9 passed |
| `uv run python scripts/validate_fixtures.py` | 通过，3 个合成 Fixture |
| `uv run python scripts/check.py` | 通过 |
| Git archive 全新环境安装与门禁 | 通过，8 passed |
| `uv build` + 全新 venv wheel 安装/import | 通过，版本 0.0.1 |
| `docker run --rm python:3.12-slim python --version` | 通过，Python 3.12.13 |
| `actionlint` Docker 静态检查 | 通过，无诊断输出 |
| GitHub Actions quality Run #4 | 通过，commit `42238c1`，10s |
| `git ls-remote origin refs/heads/main` | 本地与远端 `main` 同步 |
| Apache-2.0 官方正文比对 | 通过 |
| 安装包 `License-Expression` | `Apache-2.0` |
| wheel 许可证文件 | 包含 `dist-info/licenses/LICENSE` |
| `v0.0.1^{}` | `42238c1072675763d59a3c6455896eaa289f6b1a` |

## 当前限制

- M0 仅提供工程骨架；LangGraph、RAG、实验、论文、Web 和部署能力尚未实现。

## 下一步

先冻结 M1.1 的 Schema、State 与 Reducer 行为测试，再进入 SQLite Repository。
