# M1 学习日志：可恢复的科研项目图

## 新概念

LangGraph 的 `State` 是一次研究工作流在节点之间传递的共享契约；`Node` 是读取 State 并返回局部更新的函数；`Edge` 决定下一步执行哪个 Node；`Reducer` 决定同一字段的旧值和新值如何合并；`Checkpointer` 按 `thread_id` 保存每一步图状态，使进程退出后仍可继续。

`Tool` 是节点可调用的受控外部能力，例如查询 Repository；它不是流程节点本身。`Subgraph` 是可复用、可独立测试的子流程。M2 将引入 `interrupt` 暂停图并等待人工输入，再用 `Command(resume=...)` 恢复；这些能力在 M1 尚不可用。

## 在 ScholarTrace 中解决的问题

研究问题的形成不是一次字符串生成。它需要保留输入、约束、未知项和成功标准，并允许同一个项目在进程重启后继续。M1 用严格的 `ResearchQuestion` 拒绝空白核心字段，用 `ResearchProjectState` 隔离不同项目的控制状态，再由后续批次的 Repository 和 Checkpointer 提供双层持久化：领域实体负责可查询记录，Checkpoint 负责图执行位置。

## 核心数据如何流动

农业视觉项目输入先进入 `intake` Node，形成待处理问题；`build_research_question` Node 生成经过 Pydantic 校验的草案；`save` Node 把正式实体交给 Repository，并只把实体 ID 留在 State。Edge 按固定顺序连接这些 Node。每一步由 Checkpointer 以 `thread_id` 保存，而 `project_id` 用于领域数据隔离。

## 为什么选择当前方案

- `extra="forbid"` 让拼错或擅自新增的科研字段立即失败；
- 必填文本会去除首尾空白，核心列表不能为空，避免“结构完整但内容为空”；
- 标识符只允许安全的 ASCII 字母、数字、点、下划线和连字符，避免把路径片段误作项目 ID；
- 消息使用 `add_messages`，相同消息 ID 可以纠正而不会重复；
- 其余集合使用有序去重 Reducer，兼顾重放幂等性和可读顺序；
- 工厂函数显式构造每个列表，避免不同项目共享可变默认值。

## 最小运行示例

```python
from scholartrace.schemas import ResearchQuestion
from scholartrace.states import new_research_project_state

state = new_research_project_state("lychee-pest-001", "lychee-pest-001")
state["draft_research_question"] = ResearchQuestion(
    problem="复杂果园背景中的荔枝病虫害小目标检测",
    target_population_or_domain="华南荔枝果园图像",
    inputs=["RGB 果园图像"],
    expected_outputs=["病虫害类别", "目标边界框"],
    constraints=["类别体系待领域人员确认"],
    success_criteria=["独立测试集指标可复算"],
    assumptions=["正式数据已获得合法授权"],
    unresolved_questions=["小目标尺寸分层阈值如何确定"],
)
```

这段代码只构造内存状态，不代表数据已写入 SQLite 或图已运行。

## 常见错误与测试

- 空字符串被误当成完整研究问题：必填文本和列表项都有非空校验；
- 节点重试产生重复警告或 ID：Reducer 的重放测试验证有序去重；
- 修改一个项目影响另一个项目：工厂隔离测试验证列表互不共享；
- 把本机路径当作标识符：非法斜杠、反斜杠和前导空格会被拒绝；
- 把 State 当数据库：架构测试和后续 Repository 契约将保持实体内容与图控制状态分离。

## Repository 与 Checkpointer 的边界

Repository 保存可查询的领域事实，例如项目身份和研究问题版本；Checkpointer 保存图在某个 `thread_id` 上执行到哪里。两者不能互相替代：只保存 Checkpoint 会让领域查询依赖图内部格式，只保存业务表则无法可靠恢复节点执行位置。

M1 的 Repository 为规范化后的研究问题计算 SHA-256。同一项目重复提交完全相同的内容时返回已有记录，因此重试不会制造假版本；同一内容在不同项目中仍获得不同实体 ID。Alembic 管理 Schema 版本，测试覆盖重复升级、回滚到 base 和重新升级，避免把“能新建数据库”误当成“迁移可用”。

## 当前 Graph 的真实节点

`intake` 读取 State 的 `project_id`、`thread_id` 和 `current_goal`，通过 Repository 幂等创建项目。`build_research_question` 不调用外部模型，而是确定性地验证调用方提交的结构化草案。`save` 保存研究问题，并用实体 ID 替换 State 中的完整草案。三个普通 Edge 固定连接，没有隐藏路由。

每次 `invoke` 都由 State 自身的 `thread_id` 构造 Checkpointer config。重复运行同一输入会执行相同三个 Node，但 Repository 内容哈希保证只有一个研究问题版本。Checkpoint 和业务表的项目隔离测试都使用两个真实 thread，而不是 mock。

## 与前后里程碑的关系

M0 提供可安装工程和质量门禁。M1.1 冻结 State、ResearchQuestion 和 Reducer 语义；M1 后续批次将补齐 Repository、最小 Graph、SQLite Checkpointer、CLI 和独立进程恢复。M2 才增加条件 Edge、人工审批、`interrupt`、`Command` 和版本回滚。
