# M0 独立审查

- 日期：2026-08-09（Asia/Shanghai）
- 审查对象：`724de3549b40bcc42b11399db924f7b35860016b`
- 审查结论：`passed`。代码、本地与独立环境门禁、远端同步、CI、许可证与 Tag 均满足 M0 要求。

## 审查矩阵

| 维度 | 证据 | 结论 |
|---|---|---|
| 范围 | `src/scholartrace/` 只有包元数据和 M0 Fixture 契约 | 通过；未提前实现 M1+ |
| 安装 | Git archive 全新环境锁定安装、wheel 新 venv 导入 | 通过 |
| 单元/集成 | 7 unit + 1 integration，8 passed | 通过 |
| Fixture | 3 个合成/脱敏农业视觉项目，Schema 与负路径完整 | 通过 |
| Schema/兼容 | `schema_version=1.0`、未知字段拒绝；M0 无持久化 DB，迁移不适用 | 通过（M0 范围） |
| 错误/退化 | 损坏 JSON、数量不足、重复 ID、绝对路径、未知字段均失败并保留错误 | 通过 |
| 安全 | 秘密模式、禁止产物、大文件扫描均为 0 | 通过 |
| 科研真实性 | Fixture 强制 `fixture_only_not_research_evidence` 和 `real_world_validation=false` | 通过 |
| 文档 | README、范围、架构、ADR、风险、学习、状态、追溯、验证存在 | 通过 |
| CI | quality Run #1，commit `7b26e2d`，14s | 通过 |
| Git 同步 | 本地与远端 `main` 均为 `7b26e2d` | 通过 |
| LICENSE | Apache-2.0 正文、元数据和 wheel 文件 | 通过 |
| Tag | annotated Tag `v0.0.1`，peeled commit `42238c1` | 通过 |

## 退化与恢复

- pytest 全局临时目录无权限时，项目使用被忽略的仓库内 `.pytest-tmp/`，测试可继续且不污染 Git。
- 远端同步失败时保留本地提交和准确错误，不把本地检查描述为远端成功。
- 许可证确认后以独立小提交添加 `LICENSE` 和对应状态记录，再重新运行完整门禁。

## M0 结论

M0 已通过并发布。下一步创建 M1 功能分支；不得因此把 M1–M12 或整个项目标记为完成。
