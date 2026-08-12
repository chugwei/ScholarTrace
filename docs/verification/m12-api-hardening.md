# M12 API 健壮性修复验收

日期：2026-08-11（Asia/Shanghai）

## 范围

本批次修复批量测试中发现的两个 HTTP 错误码映射缺陷。两者都不影响科研产出的正确性与数据完整性，但破坏了 API 契约：服务端校验异常被冒泡为 500，而非语义正确的 4xx/409。

## 缺陷与根因

### 缺陷 1：非法标识符返回 500 而非 422

`ProjectCreateRequest.project_id` 与 `thread_id` 仅声明为 `NonBlankText`，不校验标识符格式。含空格、斜杠、分号等非法字符的非空串穿过 Pydantic 校验，在 `ProjectRepository.create_project` → `validate_identifier` 抛 `ValueError`，而 `create_project` 路由只捕获 `ProjectIdentityConflictError`，`ValueError` 冒泡成 500。

### 缺陷 2：并发研究问题版本递增返回 500 而非 409

`save_research_question` 用 `func.max(version)` 读后写 `version + 1`。并发下两个事务读到相同 `latest_version`，都尝试写入同一 `(project_id, version)`，触发 `UniqueConstraint("project_id", "version")` 的 `IntegrityError`。该方法未捕获 `IntegrityError`（对比 `create_project` 已有捕获），异常冒泡成 500。成功的版本号仍连续无重复，故无数据损坏。

## 修复

- `identifiers.py` 导出 `IDENTIFIER_PATTERN` 作为单一事实来源。
- `schemas/research.py` 增加 `IdentifierText` 注解绑定该 pattern；`schemas/api.py` 的 `ProjectCreateRequest` 用 `IdentifierText` 约束 `project_id` 与 `thread_id`，使非法标识符在入口被拒为 422。
- `api/app.py` 的 `create_project` 增加 `except ValueError → 422` 兜底；`save_research_question` 增加 `except ResearchQuestionConcurrentUpdateError → 409`。
- `persistence/repository.py` 新增 `ResearchQuestionConcurrentUpdateError(ProjectRepositoryError)`，`save_research_question` 捕获 `IntegrityError` 并映射为该可重试冲突错误。

## 验收命令与结果

```text
uv run pytest tests/integration/test_m11_api.py -k "rejects_invalid or concurrent_question" -q
2 passed

uv run python scripts/check.py
187 passed（基线 185 + 新增 2）；Ruff format/lint 通过；3 个合成 Fixture 通过
```

端到端复测（实际服务，30 路并发）：

```text
缺陷 1：bad id! / with/slash / semi;colon -> 422 / 422 / 422（原 500）
缺陷 2：并发 30 个研究问题 -> {201: 18, 409: 12}，全部 in {201, 409}，无 500（原 14 个 500）
```

## 证据边界

修复仅涉及 HTTP 错误码映射与请求契约，不引入新的科研能力，不改变证据分层、Claim 来源绑定或数值回溯门禁。`synthetic_fixture` 证据边界不变；`real_field` 记录仍需用户提供真实数据与环境。
