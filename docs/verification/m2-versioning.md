# M2.4 研究问题冻结与版本验证记录

- 日期：2026-08-10（Asia/Shanghai）
- 分支：`feat/m2-human-approval`
- 环境：Windows，CPython 3.12.13，LangGraph 1.2.10，SQLAlchemy 2.x

## 验证范围

- `0003` 为研究问题增加 `draft/frozen`、冻结 actor/时间和父版本列；
- `0003 → 0002 → 0001 → base → head` 的迁移回滚和重复升级；
- frozen 版本同 actor 冻结幂等，不同 actor 或过期父版本拒绝；
- frozen 版本不能被普通保存覆盖，显式父版本调用生成新 draft；
- 审批图批准已有 frozen 研究问题的修改后创建并冻结新版本，旧版本内容和父链保持不变；
- 每个版本仍以 canonical payload 的 SHA-256 派生稳定 ID，内容相同的重放不增加版本。

## 证据

```text
uv run pytest tests/integration/test_project_repository.py tests/integration/test_m2_decision_graph.py -q
29 passed

uv run python scripts/check.py
Ruff format: 39 files already formatted
Ruff lint: All checks passed
pytest: 75 passed
Fixture validation: 3 synthetic fixtures passed
```

验证数据使用合成、脱敏农业视觉 Fixture，不等同于真实场景结果；本记录对应 M2.4 当时的检查点，M2.5 和 M2.6 的后续证据见 `m2-history-rollback.md` 与 `m2-release-candidate.md`。
