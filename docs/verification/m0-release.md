# M0 v0.0.1 发布记录

- 发布日期：2026-08-09（Asia/Shanghai）
- 版本：`v0.0.1`
- 发布提交：`42238c1072675763d59a3c6455896eaa289f6b1a`
- Annotated Tag object：`19e4bc91dc2025181fe7cf8b682b25b657abeafd`
- Tag URL：<https://github.com/chugwei/ScholarTrace/tree/v0.0.1>
- CI：[quality Run #4](https://github.com/chugwei/ScholarTrace/actions/runs/31314209462)，success，10 秒

## 发布门禁

| 门禁 | 结果 |
|---|---|
| Python 3.12 锁定安装 | 通过 |
| Ruff format/check | 通过 |
| pytest | 9 passed |
| 农业视觉 Fixture | 3/3 |
| 独立 Git archive 环境 | 通过 |
| 独立 wheel 安装 | 通过 |
| Apache-2.0 正文、元数据、wheel 文件 | 通过 |
| actionlint | 通过 |
| GitHub Actions | 通过 |
| 内部路径、Secret、大文件扫描 | 0 |
| 本地/远端 main 同步 | 通过 |
| Tag peeled commit | 与发布提交一致 |

## 构建证据

| Artifact | SHA-256 |
|---|---|
| `scholartrace-0.0.1-py3-none-any.whl` | `16472908E691DCDF09979D01C05F22CDD869B0C4530F8365EC8D960669C38A16` |
| `scholartrace-0.0.1.tar.gz` | `22A262C954F2BA9E667D01AF663E16D3EFECA5EED61773BF7A0952898BB1660E` |

哈希对应发布候选独立构建；构建产物未提交到 Git。

## 能力边界

`v0.0.1` 提供可安装工程骨架、治理与真实性约束、三个合成/脱敏农业视觉 Fixture、确定性校验、测试、CI 和 Apache-2.0 许可。LangGraph、持久化项目图、RAG、实验、论文、Web 和部署能力尚未实现。

下一版本 `v0.1.0` 将在 `feat/m1-project-state` 分支实现最小持久化科研项目图。
