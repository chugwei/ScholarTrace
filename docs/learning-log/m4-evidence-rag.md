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

## M4.2 Chunk、BM25 与 Vector

全文不能直接塞入 Graph State，也不能只保存“命中标题”。`DocumentChunk` 用字符偏移、序号和内容哈希把检索结果绑定回运行时文本；农业视觉黄金样例中的每个荔枝病虫害片段都可以用 `text[start_offset:end_offset]` 重建。固定窗口加重叠区间是当前的最小确定性方案，后续可以替换分词器而不改变来源字段契约。

BM25 使用每个 Chunk 的词频、文档频率和平均长度计算 lexical score；Vector provider 将同一文本映射为固定维度向量并计算 cosine score。当前 `HashingEmbeddingProvider` 不访问网络、不需要 API Key，适合 CI 重放，但它只证明接口、排序和降级行为，不证明语义召回质量。正式基线留给 M4.3 的固定 10–20 条回归集和人工标注。

索引重建分成“构造候选快照 → 写临时文件 → 原子替换”三个步骤。Vector 服务异常时构造阶段直接失败，active 文件不变；查询者仍能读取上一代 `index_generation`。这比先删除旧索引再重建更适合科研工作台：失败不会让已有项目暂时失去可追溯检索。

```python
index = HybridChunkIndex(runtime_index_root)
snapshot = index.rebuild_project("lychee-m4", repository)
hits = index.search("lychee-m4", "lychee disease", top_k=5)
source_text = load_runtime_text_for(hits[0].chunk.document_id)
assert (
    source_text[hits[0].chunk.start_offset : hits[0].chunk.end_offset]
    == hits[0].chunk.text
)
```

M4.2 的索引仍不是 Rerank，也没有 EvidenceCard 或引用解析；下一批次会把 DOI/URL/原文片段校验作为进入可信证据集的第二道门。

## M4.3 EvidenceCard 与来源链

EvidenceCard 的核心不是“写一段听起来合理的话”，而是把一条项目 statement 绑定到 approved DocumentChunk 的精确 SourceSpan。服务先检查项目审核状态，再用 `str.find()` 定位 quote，计算文档绝对偏移，并从 DOI、URL 或安全的本地相对路径中选择 locator。配置源文本根目录时，系统还会重新读取文本并比对偏移片段；文件被篡改或 quote 不在 Chunk 中都会失败。

这一步把引用校验和生成内容分开：EvidenceCard 只保存经过结构和来源校验的记录，statement 本身仍由研究者负责，不代表自动证明了因果关系、统计显著性或创新性。重复提交相同项目、Chunk、片段和 statement 返回已有卡片，避免重试制造重复证据。

固定回归集包含 10 条合成农业视觉查询，覆盖荔枝病害、麦田产量和果园计数三个主题。它验证当前离线 hashing vector + BM25 的 top-1 可重复性，不等同于真实文献 Top-k 基线；后续应使用人工标注的真实或授权语料替换/扩展回归集。

M4.3 与 LangGraph 的关系仍保持清晰：EvidenceCardService 是可重放的领域服务，不是自动放行的 Node；未来 Graph Node 可以调用它，Edge 可以根据“待补来源/已验证”路由，但 Checkpointer 不能替代数据库中的来源审计。
