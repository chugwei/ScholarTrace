# M4 学习日志：项目文献筛选与可信证据

M4 的第一批次把全局文献目录和项目证据边界连接起来。文献目录可以包含重复、解析失败和无关条目；只有项目范围内经过人工审核的 `approved` 关联才允许进入后续证据检索。M4.1 尚未实现 Chunk、向量检索、Rerank 或 EvidenceCard，因此不能把相关度排序称为 RAG 或科研结论。

## M4.1 解决的真实问题

以农业视觉的荔枝病虫害识别项目为例，同一个文献可能被多个项目复用，且上传文件的解析质量不同。`Document` 保持全局身份和内容哈希，`ProjectDocument` 保存项目自己的候选关系。这样一个项目拒绝文献不会改变另一个项目的判断，也不会把解析失败的文件误送进正式证据集。

## 数据流

```text
全局 documents
    ↓ attach_document()
项目 project_documents(candidate)
    ↓ rank_project_candidates(query)
确定性元数据相关度排序
    ↓ 人工 review_project_document()
approved / rejected + actor + reason + timestamp
    ↓ list_approved_documents()
M4.2 的 Chunk/全文检索入口
```

相关度是标题、作者、摘要和 DOI 的 token overlap：

```python
ranked = repository.rank_project_candidates(
    "lychee-m4",
    "lychee disease",
)
review = repository.review_project_document(
    "lychee-m4",
    ranked[0].document.document_id,
    status="approved",
    actor_id="researcher-001",
    reason="标题和研究域与黄金问题一致",
    relevance_score=ranked[0].score,
)
approved = repository.list_approved_documents("lychee-m4")
```

这里的分数只负责稳定排序，不是语义相似度、质量判断或创新性证明。人工理由和审核者是可追溯门槛；全局 `Document` 不会因项目审核而被修改。

## 为什么使用 Repository 门禁

`LiteratureRepository` 是事务边界和数据完整性工具，不是 LangGraph Node。它要求关联先处于 `candidate`，只接受 `approved` 或 `rejected` 的终态；空白理由、越界分数和不存在的关联都会失败。`approved` 还要求全局文献不是 `failed` 且可搜索。0005 迁移可回退到 0004，再升级回 head，避免仅靠 Python 默认值掩盖 Schema 不一致。

M4.1 没有新增 Graph State、Edge 或 Checkpointer：项目文献审核目前是可独立复用的领域服务。后续若接入 LangGraph，Node 应调用这个 Repository，Edge 只表达“候选待审核/已批准”的控制流，不能绕过事务门禁。

## 概念边界

- **State**：跨节点传递的轻量控制数据；M4.1 不把全文或检索索引放进 State。
- **Node**：一次可重放的业务步骤；M4.1 的排序和审核是 Repository 服务调用，不冒充 Graph Node。
- **Edge**：根据状态选择下一步；后续证据子图可依据 `approved` 数量路由。
- **Reducer**：合并 Graph State 更新；本批次没有新增 Reducer。
- **Checkpointer**：保存 Graph 运行快照；项目文献审核记录保存在业务数据库，不能用 checkpoint 替代审计。
- **Tool**：执行外部或确定性操作；M3 的元数据客户端属于 Tool 边界，M4.1 的 token 计算是本地纯函数。

## 常见错误与测试

最危险的错误是把“目录命中”或“候选排序第一”直接当成可信证据。集成测试验证候选只在项目范围内排序、批准列表只返回显式 `approved`、失败文献不能批准、空白理由被拒绝，以及 0005 迁移的升级/回滚。测试数据是合成/脱敏农业视觉条目，不代表真实论文或现场结果。

M3 提供全局目录、PDF 质量标记和外部元数据降级；M4.1 增加项目级人工筛选；M4.2 将在 approved 文献上建立 Chunk/全文索引，M4.3 再加入 EvidenceCard 和固定检索回归。
