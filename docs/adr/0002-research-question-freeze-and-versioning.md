# ADR 0002：研究问题冻结与显式新版本

- 状态：已接受
- 日期：2026-08-10
- 范围：M2.4 研究问题生命周期

## 背景

人工批准后的研究问题是后续管线、数据协议和实验计划的依据。若普通保存可以直接改变它，历史审计只能看到最后内容，无法证明哪一版曾经得到确认。另一方面，重试同一写入必须保持幂等，不能因为网络重放产生重复版本。

## 决策

每个项目的研究问题版本使用 `draft` 或 `frozen` 状态。批准动作保存并冻结当前版本；冻结版本不能通过普通 `save_research_question()` 写入不同内容。修改必须调用 `create_research_question_version()`，父 ID 必须指向当前冻结版本，生成新的 draft，随后由人工审批决定是否冻结。

版本 ID 继续使用项目 ID 与规范化 payload 的 SHA-256，内容不变时重放返回已有版本，内容改变时递增项目内版本号。Repository 记录 `parent_research_question_id`、冻结时间和 actor，形成可查询的版本链。

## 取舍

- `draft/frozen` 足以支持 M2 的审批门禁；更细的 archived/superseded 状态留给后续领域实体，避免过早扩大 Schema。
- 父版本暂不使用跨表强制外键，Repository 在同一项目内校验父版本，迁移保持 SQLite 旧数据库可回滚。
- Checkpoint 仍保存工作流状态，领域版本和冻结元数据存放在业务 SQLite；两者分离便于独立审计和重建。

## 验证

`tests/integration/test_project_repository.py` 验证升级/回滚、冻结幂等、冻结后拒绝隐式修改、父版本校验和版本链；`tests/integration/test_m2_decision_graph.py` 验证批准修改版本后得到新的 frozen 记录。合成农业视觉 Fixture 仅证明流程和数据契约，不构成真实果园结果。
