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
