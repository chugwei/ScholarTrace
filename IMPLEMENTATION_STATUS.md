# ScholarTrace 实施状态

- 项目状态：M0 发布准备中
- 当前里程碑：M0 — 问题定义与仓库骨架
- 当前版本：`0.0.1`（尚未发布 Tag）
- 当前分支：`main`
- 远端：<https://github.com/chugwei/ScholarTrace.git>
- 最近已推送检查点：`b6e07ed27ca422dddc2a06444ee8735e8688ec8b`
- 最近已记录本地检查点：`2ea52610d117d7db2cc566aaa50efe7e0c92b1e8`
- 更新时间：2026-08-09（Asia/Shanghai）

## 已完成

- 初始化独立仓库并配置 `main` 与 `origin`。
- 建立 Python 3.12、uv、src layout、pytest 与 Ruff 工程骨架。
- 完成产品范围、非目标、科研真实性、风险、ADR 和贡献规范。
- 建立三个农业视觉合成/脱敏 Fixture 及严格 Schema 校验。
- 建立本地统一质量门禁和最小权限 GitHub Actions workflow。
- 完成 Git archive 独立源码安装、sdist/wheel 构建与全新 venv 安装验收。
- 实际运行 Python 3.12 与 `actionlint` 容器。

## M0 小任务

- [x] M0.1 仓库与可安装 Python 骨架
- [x] M0.2 范围、非目标、风险、真实性与开发约定
- [x] M0.3 农业视觉黄金场景、3 个脱敏 Fixture 及校验
- [ ] M0.4 Ruff、pytest、CI 与降级测试（本地完成，远端 CI 待运行）
- [x] M0.5 全新环境验收、工程记录、追溯矩阵和独立审查
- [ ] M0.6 许可证确认、`main` 推送与 `v0.0.1` Tag

## 当前验证

| 命令 | 结果 |
|---|---|
| `uv sync --all-groups` | 通过，CPython 3.12.13 |
| `uv run ruff format --check src tests scripts` | 通过 |
| `uv run ruff check src tests scripts` | 通过 |
| `uv run pytest` | 通过，8 passed |
| `uv run python scripts/validate_fixtures.py` | 通过，3 个合成 Fixture |
| `uv run python scripts/check.py` | 通过 |
| Git archive 全新环境安装与门禁 | 通过，8 passed |
| `uv build` + 全新 venv wheel 安装/import | 通过，版本 0.0.1 |
| `docker run --rm python:3.12-slim python --version` | 通过，Python 3.12.13 |
| `actionlint` Docker 静态检查 | 通过，无诊断输出 |
| `git ls-remote origin refs/heads/main` | 远端为 `b6e07ed...`，本地存在未推送提交 |

## 发布阻塞

- `LICENSE` 尚未确定；许可证会影响公开复用边界，发布 Tag 前必须确认。
- 本地版本尚未同步到远端，GitHub Actions 尚未运行。
- GitHub Actions 尚未运行，不能把本地检查或静态 workflow 校验描述成远端 CI 通过。
- M0 仅提供工程骨架；LangGraph、RAG、实验、论文、Web 和部署能力尚未实现。

## 下一步

确认许可证并同步 `main` 后，依次核验远端 CI、添加 `LICENSE`、重跑 M0 门禁、创建并推送 `v0.0.1`，随后开始 M1 功能分支。
