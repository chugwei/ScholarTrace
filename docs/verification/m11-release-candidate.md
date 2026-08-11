# M11 `v0.11.0` 发布候选审查

日期：2026-08-11（Asia/Shanghai）

## 范围

候选版本为 `v0.11.0`，包含 Project/Run/Artifact API、可重放和实时 SSE Run 时间线、URL 项目恢复、内嵌 Web 工作台、四个 SectionContract 论文草稿和人工审阅门禁。浏览器垂直验收使用合成/脱敏农业视觉项目，不能当作真实文献、真实实验或生产部署证据。

## 验收命令与结果

| 检查 | 结果 |
|---|---|
| `uv run ruff format --check src tests scripts` | 通过，129 files already formatted |
| `uv run ruff check src tests scripts` | 通过，All checks passed |
| `uv run python scripts/check.py` | 通过，166 passed；3 个合成 Fixture；ScholarTrace quality gate passed |
| `uv build --out-dir .verification/m11-rc-dist-20260811` | 通过，生成 `scholartrace-0.11.0.tar.gz` 和 `scholartrace-0.11.0-py3-none-any.whl` |
| wheel/sdist 内部文件排除 | 通过；计划、Prompt、`AGENTS.md`、`docs/goal-progress.md` 均为 0；wheel 包含 Apache-2.0 license 文件 |
| 独立 venv 安装 wheel、import、CLI | 通过，package/metadata version `0.11.0`，`License-Expression=Apache-2.0`，`scholartrace --help` 与 `scholartrace web --help` exit 0 |
| 独立迁移升级/回滚 | 通过，`head=0018; rollback=0017; head_again=0018` |
| Docker Python smoke | 通过，Python 3.12.13 |
| Docker actionlint | 通过，1.7.7 无诊断 |
| 秘密与大文件扫描 | 通过；Token/Cookie/密钥模式 0 matches，tracked >5MB 为 0 |
| 浏览器垂直验收 | 通过；详见 `docs/verification/m11-workbench.md`，包含截图/DOM 和 `live=true` 增量事件证据 |

## 独立审查结论

- `pyproject.toml`、包 `__version__`、测试和 `uv.lock` 均为 `0.11.0`，许可证保持 Apache-2.0。
- API、工作台和 Manuscript Repository 复用既有迁移与项目隔离；页面只展示 Repository 状态，不绕过 frozen plan、证据或 Claim 门禁。
- 有限 SSE 用于快照/重放，工作台显式使用 `live=true` 长连接；未知 Run、非法游标、事件解析失败和连接断开都有降级路径。
- 公开构建不包含本地计划、执行 Prompt、`AGENTS.md`、进度文件、凭据、数据库、论文全文、运行产物或模型权重。
- M11 只证明合成/脱敏演示和本地浏览器验收；M12 仍必须完成交付包、独立部署、回滚和真实场景验证。

候选通过后，才允许合并 `main`、运行 main smoke、创建并推送 annotated `v0.11.0` Tag。
