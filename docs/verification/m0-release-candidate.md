# M0 v0.0.1 发布候选验收

- 日期：2026-08-09（Asia/Shanghai）
- 源提交：`724de3549b40bcc42b11399db924f7b35860016b`
- 结论：发布候选的本地、独立环境、构建、许可证、安全与远端 CI 门禁通过；正式 Tag 尚待创建。

## 独立源码环境

从 Git commit 导出干净 ZIP，在新目录中执行：

```text
uv sync --frozen --all-groups
uv run python scripts/check.py
uv build
```

实际结果：

- CPython 3.12.13；
- Ruff format/check 通过；
- pytest：9 passed；
- 合成/脱敏 Fixture：3/3；
- sdist 与 wheel 构建成功。

## 独立 wheel 环境

在第二个空 venv 中安装构建出的 wheel，验证：

- `scholartrace.__version__ == "0.0.1"`；
- `License-Expression == "Apache-2.0"`；
- wheel 包含 `scholartrace-0.0.1.dist-info/licenses/LICENSE`。

构建哈希：

| Artifact | SHA-256 |
|---|---|
| `scholartrace-0.0.1-py3-none-any.whl` | `16472908E691DCDF09979D01C05F22CDD869B0C4530F8365EC8D960669C38A16` |
| `scholartrace-0.0.1.tar.gz` | `22A262C954F2BA9E667D01AF663E16D3EFECA5EED61773BF7A0952898BB1660E` |

哈希对应本次发布候选构建；正式发布包如重新构建，必须重新生成并记录哈希。

## 许可证与 CI

- `LICENSE` 与 Apache License 2.0 官方正文一致，仅替换 Appendix 版权占位符；
- `actionlint .github/workflows/quality.yml` 无诊断；
- GitHub Actions [quality Run #3](https://github.com/chugwei/ScholarTrace/actions/runs/31314076022) 成功；
- Run #3 对应 commit `724de3549b40bcc42b11399db924f7b35860016b`，耗时 9 秒。

## 仓库卫生

| 检查 | 结果 |
|---|---|
| 私有工作文件路径 | 0 |
| Secret 模式 | 0 |
| 大于 5 MB 的跟踪文件 | 0 |
| 工作树 | 干净，本地与远端同步 |

## 剩余发布步骤

1. 提交本验收记录并等待该提交的 quality workflow；
2. 创建并推送带注释 Tag `v0.0.1`；
3. 核验远端 `main` 与 Tag；
4. 更新发布后状态并开始 M1。
