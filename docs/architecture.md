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

业务数据库与 checkpoint 数据库是两个文件：前者保存项目和研究问题版本，后者由 `SqliteSaver` 保存节点执行快照。关闭两个连接后重新打开，领域实体和最终 State 都能恢复；两个 thread 的 checkpoint 查询互不串联。本批次只实现固定 Edge，不包含人工暂停或条件路由。
