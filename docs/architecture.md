# 架构基线

## 当前结构

```text
ScholarTrace
├── src/scholartrace/       可安装 Python 包与 M0 Fixture 契约
├── tests/                  单元、集成和合成 Fixture
├── scripts/                本地/CI 统一门禁与 Fixture 校验
├── examples/               农业视觉黄金场景说明
├── docs/                   范围、ADR、学习、验证和追溯记录
└── .github/workflows/      最小权限 CI
```

M0 不包含 Graph、业务数据库、文献索引、实验 Runner、论文生成、API 或前端。对应目录将在各自里程碑有可执行契约和测试时创建，避免提前制造空壳能力。

## M0 数据流

```text
JSON Fixture
  → UTF-8/JSON 解析
  → Pydantic ProjectFixture 校验
  → 数量与 project_id 唯一性校验
  → 仅输出已验证 Fixture ID
```

校验器拒绝未知字段、真实现场验证声明、私有数据声明和机器特定绝对路径。Fixture 不进入任何文献、实验或论文流程。

## 后续演进边界

- M1 增加 State、Node、Edge、Reducer、Checkpointer 和 Project Repository；
- M3 才增加独立文献库与文件持久化；
- M4 才增加 approved 证据检索；
- M7–M10 才增加真实实验产物、图表和论文；
- M11–M12 才增加 Web、容器部署和真实场景交付。

所有演进必须通过 ADR、测试、迁移/兼容验证和版本 Tag 固定。

## M1 状态契约

`ResearchProjectState` 是 LangGraph 节点之间的小型控制平面。它保存项目和线程标识、当前阶段、待处理事项以及领域实体 ID，不保存 PDF、数据集、模型权重、长日志或论文全文。`draft_research_question` 是 M1 构建问题时唯一保留在 State 中的结构化草案；正式保存后由 Repository 分配 ID。

State 中的消息使用 LangGraph `add_messages` Reducer：相同消息 ID 的更新会替换旧消息。警告、下一动作和实体 ID 列表使用有序去重 Reducer，使节点重放和重试不会重复追加同一个值。`new_research_project_state()` 每次创建独立容器，防止项目之间共享可变列表。

## M1 业务持久化

业务实体使用 SQLite、SQLAlchemy 2 和 Alembic。`projects` 保存项目与线程的一对一身份关系；`research_questions` 保存通过 Schema 校验的研究问题版本、内容 SHA-256 和 JSON payload。Repository 的每次公开操作使用短事务，同一项目重复保存相同内容时返回原记录，不增加版本；内容改变时才分配下一版本。

研究问题查询必须同时匹配 `project_id` 和 `research_question_id`，防止跨项目读取。数据库启用 SQLite 外键约束；初始迁移支持 upgrade、downgrade 到 base 和再次 upgrade。业务数据库属于运行数据，由 `.gitignore` 排除，不进入源码历史。

## M1 最小 Graph

```text
START → intake → build_research_question → save → END
```

`intake` 幂等创建项目记录，`build_research_question` 再次执行 Pydantic 契约校验，`save` 通过 Repository 保存内容并把 `research_question_id` 写回 State。运行入口只从已校验的 State `thread_id` 生成 LangGraph config，调用方不能额外传入冲突的 checkpoint thread。

`save` 在同一 Repository 事务中保存研究问题并把 Project 的 `active_stage` 更新为 `completed`，因此 `project show` 的业务视图和 Graph 最终 State 不会分别停留在 `intake` 与 `completed`。

业务数据库与 checkpoint 数据库是两个文件：前者保存项目和研究问题版本，后者由 `SqliteSaver` 保存节点执行快照。关闭两个连接后重新打开，领域实体和最终 State 都能恢复；两个 thread 的 checkpoint 查询互不串联。本批次只实现固定 Edge，不包含人工暂停或条件路由。

## M2.1 缺失信息路由

M2.1 在研究问题输入进入校验前计算缺失字段，不用模型补全。`find_missing_question_fields()` 按 ResearchQuestion 契约顺序检查必填文本、核心列表和结构化列表；Conditional Edge 将结果路由到 `clarify` 或原有 `build_research_question → save` 路径。`clarify` 只写入 `awaiting_clarification` 和下一动作，不写入 ResearchQuestion 实体。

这一步仍不是人工暂停：`clarify` 在本批次到达 `END`，没有 `interrupt()`、DecisionRecord 或恢复输入。M2.2 才会把同一分支改成持久化等待，并验证人工输入恢复后能清理旧的 `pending_questions`。

## M2.2 真正暂停与恢复

M2.2 的 `clarify` 节点调用 `interrupt()` 返回结构化 `kind`、缺失字段和当前 payload。第一次运行只提交 checkpoint，不写正式研究问题；客户端必须用同一 `thread_id` 和 `Command(resume=answer)` 恢复。恢复会从 `clarify` 节点开头重放，合并人工补充后回到 `intake`，重新计算缺口，再决定保存或再次暂停。

`pending_questions` 从 M2.2 起使用替换型 Reducer：它代表当前缺口集合，而不是历史并集。历史审计不依赖这个字段。

## M2.3 审批与 DecisionRecord

M2.3 在研究问题完整后进入独立的审批图：

```text
START → intake ──(缺字段)──> clarify ──> intake
             └─(完整)────> request_decision → apply_decision
                                             ├─ approved → save → END
                                             ├─ modified → request_decision
                                             └─ rejected/cancelled/paused → finish → END
```

`request_decision` 的 `interrupt()` 请求包含目标类型、稳定的待审批目标 ID、当前 payload 和允许动作；恢复值必须经过 `DecisionRecord` 的结构校验，空白 actor、缺失非批准理由和未知动作都会被拒绝。`record_decision()` 在业务数据库中以 `decision_id` 做幂等键：相同内容重放返回原记录，内容冲突显式失败。

`modified` 只接受 ResearchQuestion 已知字段，先校验合并后的完整问题，再回到下一次审批；`approved` 通过 Repository 保存正式问题，其他三个终止动作只更新项目阶段并保留审计记录。SQLite 迁移可从 `0002` 回退到 `0001`，不会把 DecisionRecord 表残留在旧 Schema 中。

## M2.4 研究问题冻结与新版本

研究问题版本在 `0003` Schema 中有明确的 `draft/frozen` 状态，以及 `frozen_at`、`frozen_by` 和 `parent_research_question_id`。普通保存只创建 draft；审批图的批准分支保存后立即冻结当前版本。冻结记录不可直接写入不同内容，Repository 会要求调用 `create_research_question_version()`，并验证父版本是项目当前的 frozen 版本。

版本 ID 仍由 `project_id + canonical payload` 的 SHA-256 派生，内容相同的重放返回同一记录；内容改变时递增 `version` 并保存父版本 ID。这样荔枝病虫害研究问题从“增加雨季采集约束”得到的新版本可以回到上一冻结版本，且不会覆盖已批准的问题。`freeze_research_question()` 对同一 actor 重放幂等，对不同 actor 或过期版本显式拒绝。

## M2.5 Checkpoint History、回滚与审计

审批图 facade 暴露 `history()` / `get_state_history()`，返回同一 `thread_id` 的 LangGraph `StateSnapshot`，按新到旧排列；查询不跨线程，也不修改历史记录。`rollback(thread_id, checkpoint_id, actor_id, reason)` 先确认目标 checkpoint 属于该 thread，再使用 `update_state()` 将目标 State 写入一个新的 checkpoint。旧 checkpoint 永不被覆盖，新的 State 会保留目标的下一节点语义。

回滚完成后写入一个 `DecisionRecord(target_type="checkpoint", action="rolled_back")`，payload 同时记录来源 checkpoint、目标 checkpoint 和恢复后的阶段。`list_audit_records()` 与 `list_decisions()` 支持按 target/action 查询，因此“谁在何时把哪个 thread 从哪里恢复到哪里”可以独立于 Graph State 查询。回滚只恢复工作流 State，不删除已经批准的领域版本；若要修改研究问题，仍必须走 M2.4 的新版本审批链。
