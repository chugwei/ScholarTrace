# M0 环境基线

- 日期：2026-08-09（Asia/Shanghai）
- 检查性质：空仓库初始化前的工具链、远端和执行能力核验

## 初始仓库状态

初始化前不存在 `.git`，目录中没有既有项目代码。远端在检查时没有 heads、tags 或默认 HEAD refs，因此使用 `git init -b main` 初始化，并设置：

```text
https://github.com/chugwei/ScholarTrace.git
```

## 工具链

| 工具 | 实际结果 |
|---|---|
| Git | `2.45.2.windows.1` |
| 系统 Python | `3.13.13`（Miniconda） |
| 项目 Python | uv 管理的 CPython `3.12.13` |
| uv | `0.11.19` |
| Docker CLI/Engine | `28.3.2` |
| Node.js | `v24.14.1` |
| npm | `11.11.0` |
| GitHub CLI | 未安装 |

## 远端与认证

初始化前执行：

```text
git ls-remote --symref https://github.com/chugwei/ScholarTrace.git HEAD
git ls-remote --heads --tags https://github.com/chugwei/ScholarTrace.git
```

两个命令均成功且没有返回 refs。首次 `git push -u origin main` 成功，确认 Git Credential Manager 可以推送普通提交；未输出或记录任何凭据内容。

GitHub Actions 的真实状态只在 workflow 推送并完成运行后记录；本地静态校验不能替代远端结果。

## 基础执行能力

- Python 虚拟环境创建、锁定安装、Ruff 和 pytest 已实际运行。
- Node runtime 已实际运行。
- Docker 已实际拉取并运行 Python 3.12 与 `actionlint` 容器。
- 浏览器端到端验收属于后续 Web 版本范围，M0 不据此声明任何界面能力。
