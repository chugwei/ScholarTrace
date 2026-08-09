# M0 本地验收记录

- 日期：2026-08-09（Asia/Shanghai）
- 被验收 Git commit：`fc774da81e6e8e77f527bb4898e2ea1c1480906f`
- 结论：本地代码、Fixture、构建和独立安装门禁通过；远端 push、GitHub Actions 和 LICENSE 门禁未通过，因此 M0 尚未完成。

## 开发环境统一门禁

命令：

```text
uv run python scripts/check.py
```

实际摘要：

```text
21 files already formatted
All checks passed!
collected 8 items
8 passed in 0.16s
validated 3 synthetic project fixtures
ScholarTrace M0 quality gate passed.
```

测试包含 1 个目录级集成测试和 7 个单元测试，覆盖安装版本、三个农业视觉任务、Fixture 数量不足、重复 ID、机器绝对路径、未知字段和损坏 JSON。

## Git archive 独立源码环境

从 commit 导出 ZIP 到全新目录 `.verification/m0-clean-fc774da`，然后运行：

```text
uv sync --frozen --all-groups
uv run python scripts/check.py
uv build
```

实际结果：CPython 3.12.13 创建新 `.venv`，按 `uv.lock` 安装 13 packages；Ruff format/check 通过，`8 passed in 0.85s`，三个 Fixture 通过；成功构建：

- `scholartrace-0.0.1.tar.gz`
- `scholartrace-0.0.1-py3-none-any.whl`

构建产物只存在于被忽略的临时验收目录，不进入 Git。

## 独立 wheel 安装

在另一个空 venv `.verification/m0-wheel-fc774da` 中运行：

```text
uv pip install --python <fresh-python> scholartrace-0.0.1-py3-none-any.whl
<fresh-python> -c "import scholartrace; print(scholartrace.__version__)"
```

实际输出：`wheel import ok: 0.0.1`。

临时构建哈希：

| Artifact | SHA-256 |
|---|---|
| wheel | `C1768D0E606E1BE25B0C42884AF5AF6EEC3EBAF7DFA0F2E2D3477FEFB22AB13C` |
| sdist | `95C8194C14C92FB3EDB7BCCEB76DF74CD6E953FCD26830095A5A1E8B845BFBA7` |

这些哈希只证明本次临时构建，不是正式 v0.0.1 发布清单。

## 容器与 workflow 静态验收

命令：

```text
docker run --rm python:3.12-slim python --version
docker run --rm -v <repository>:/repo -w /repo rhysd/actionlint:latest -color
```

实际结果：首个命令返回 `Python 3.12.13`；`actionlint` 成功完成且无诊断输出。由此确认 Docker 能真实拉取并运行容器，workflow YAML 通过静态检查。GitHub Actions 仍未运行，不能由静态检查推断为远端成功。

## 安全与仓库卫生

| 检查 | 实际结果 |
|---|---|
| Secret/Token/Password/Cookie 赋值模式扫描 | 0 matches |
| 被跟踪 `.env`、数据库、权重、ONNX | 0 files |
| 被跟踪文件大于 5 MB | 0 files |
| Fixture 私有数据标志 | 全部 false |
| Fixture 真实现场验证标志 | 全部 false |

## 未通过门禁

- `.github/workflows/quality.yml` 所在本地提交尚未推送，GitHub Actions 状态为“未运行/未验证”。
- `LICENSE` 尚未创建，许可证类型仍待确认。
- `v0.0.1` Tag 未创建且不得提前创建。
