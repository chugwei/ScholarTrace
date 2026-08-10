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

## M3.1 独立文献目录

`documents` 是全局目录，`project_documents` 只是项目候选关联；M3 不把目录条目自动变成项目证据。文献 ID 由内容 SHA-256 派生，重复上传返回同一记录，项目关联使用独立稳定 ID 并保持 `candidate` 状态。

目录查询只读取 `searchable=true` 且 `ingest_status != failed` 的元数据字段（标题、作者、摘要、DOI、URL）。原始 PDF、解析文本和大型运行数据不进入数据库或 Git；M3.2 将把合法上传文件写到 `.gitignore` 覆盖的运行时存储，并显式记录解析质量。

## M3.2 PDF 入库与质量边界

`DocumentLibrary.ingest_pdf()` 先计算内容 SHA-256，再尝试用 pypdf 解析；同一内容在解析前就返回已存在条目。成功解析的 PDF 和提取文本写到调用方提供的运行时根目录，并在写入完成后设置只读权限，数据库只保存相对路径。解析失败会保存 `failed/parse_failed/searchable=false` 诊断记录，但不复制原文，也不会出现在目录搜索中。

合法上传、元数据来源和解析质量是三个独立事实：pypdf 的 `/Title`、`/Author` 和创建年份只作为可追溯元数据，缺失时标记 `metadata_incomplete`；空文本标记 `empty_text`，不能被描述成全文解析成功。M3 不自动下载受版权限制的全文，外部元数据客户端留给 M3.3。

## M3.3 外部元数据与降级

`CrossrefClient` 和 `OpenAlexClient` 实现同一个 `MetadataProvider` 契约，只返回结构化 `MetadataLookupResult`。HTTP 非 200、超时、连接异常、JSON 无结果都返回 `unavailable` 或 `not_found`，不会填充默认作者、年份或 DOI。`LiteratureMetadataService` 按调用方给定顺序尝试提供商，并保留所有 attempts，成功结果才可显式转换为 `metadata_only` Document。

元数据 Document 的 `source_type` 是 `crossref` / `openalex`，`storage_relpath` 为空，表示它不是授权全文。MockTransport 让 CI 验证真实的请求路径、字段归一化和网络失败分支；真实 API 访问不属于离线测试通过的证据。

## M4.1 项目文献审核与相关度

M4 在 M3 全局目录之上维护项目级 `ProjectDocument` 状态：新关联为 `candidate`，人工审核后才可变为 `approved` 或 `rejected`。审核记录保存 actor、时间、理由和 0–1 相关度；全局 Document 不被复制或改写，失败/不可搜索文献不能批准。

`rank_project_candidates()` 使用标题、作者、摘要和 DOI 的确定性 token overlap 评分，只用于排序候选，不声称语义相关或创新证据。项目正式文献查询通过 `list_approved_documents()`，因此 candidate 和 rejected 不会意外进入后续证据链；M4.2 才在 approved 文献上建立 Chunk 检索。

## M4.2 Chunk 与混合索引

`DocumentLibrary.index_document_text()` 从 M3 运行时保存的文本文件读取内容，用固定字符窗口和重叠区间生成 `DocumentChunk`。每个 Chunk 保存 `document_id`、稳定 `chunk_id`、序号、原文字符偏移和内容 SHA-256；`text[start_offset:end_offset]` 必须与 Chunk 文本完全一致。数据库迁移 0006 以文档和序号建立唯一约束，替换 Chunk 集合时使用一个事务。

`HybridChunkIndex.rebuild_project()` 只从 `list_approved_chunks()` 获取项目内容。索引快照同时保存 BM25 词频/文档频率、可替换 Vector provider 的向量和 Chunk 完整来源字段。默认 `HashingEmbeddingProvider` 仅用于离线、确定性验证，不是语义质量证明；部署时可以注入具有相同契约的真实向量 provider。

重建先在内存中完成并写入 `.tmp` 文件，成功后才原子替换项目的 active JSON 快照。Vector provider 异常、维度错误或序列化失败都不会触碰旧快照，因此旧索引仍可查询。搜索结果返回 Chunk、BM25 分数、Vector 分数和 `index_generation`，为 M4.3 的 EvidenceCard 片段定位保留完整链路。

## M4.3 EvidenceCard 与引用校验

`EvidenceCardService.create_card()` 首先通过 `get_approved_chunk()` 检查项目关系，随后要求用户提供的 quote 精确出现在 Chunk 中，并将 Chunk 内相对位置转换为原文绝对偏移。它从 Document 的 DOI、HTTP(S) URL 或安全的相对本地路径中选择 locator；没有可解析来源时不写卡片。配置运行时文本根目录后，还会再次读取原文并校验绝对偏移，防止存储文件被替换。

持久化的 EvidenceCard 固定为 `verified`，包含 statement、SourceSpan、locator、审核者和创建时间。它是有来源的证据记录，不是模型自动生成的科研结论；statement 仍需要研究者判断。`tests/fixtures/retrieval/m4-regression.json` 提供 10 条合成农业视觉查询，验证当前离线索引的 top-1 基线，真实文献召回仍需后续数据和人工标注。

## M5.1 版本化研究设计契约

`PipelineSpec` 把数据采集、训练、评估和交付阶段保存为有序 `PipelineStage` 列表；`DataCollectionProtocol` 描述目标群体、抽样、采集字段、标注策略、数据划分和泄漏控制。两者都使用 Pydantic `extra="forbid"`，在边界拒绝未知字段和重复 stage/field 名称，并由 Repository 计算 canonical content SHA-256。

`DesignRepository` 将每个版本写入独立 SQLite 表。新设计从 `draft` 开始；批准写入 actor、理由和时间，并把旧的 approved 版本标记为 `superseded`。批准版本不能被隐式覆盖，修改必须使用递增版本号和当前批准父 ID；相同内容重放返回原记录。0008 迁移支持完整回退，JSON payload 保留 Schema 之外的可审计原始结构。

本批次还没有研究设计 Subgraph、流程图、数据泄漏执行检查或 Markdown/YAML 导出。Repository 是领域持久化边界，不冒充 LangGraph Node；M5.2 才把这些契约接入可重放的 Subgraph 和人工发布流程。
