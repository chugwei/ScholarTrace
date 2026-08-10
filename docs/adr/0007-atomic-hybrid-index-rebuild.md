# ADR 0007：混合索引采用可替换 provider 与原子重建

- 状态：已接受
- 日期：2026-08-11
- 范围：M4.2 DocumentChunk、BM25 和 Vector 检索

## 背景

项目检索需要同时利用词法命中和向量相似度，但真实 embedding 服务可能不可用、限流或返回错误维度。重建过程中如果先删除现有索引，短暂故障就会让已经验证过的项目失去检索能力；把外部服务写死在 CI 也无法稳定复现。

## 决策

`HybridChunkIndex` 使用 `EmbeddingProvider` 协议，默认注入确定性的 `HashingEmbeddingProvider`。索引快照保存 Chunk、BM25 统计、向量、provider 名称、维度和生成号。重建在内存完成后写到同目录临时文件，成功才执行原子替换；所有构造、向量或序列化异常都保留旧 active 文件。项目入口 `rebuild_project()` 只从 `approved` ProjectDocument 读取 Chunk。

## 取舍

- 纯 Python BM25 和 hashing vector 可离线验证，部署时可替换 provider；当前 hashing 结果不能当作语义召回基线。
- JSON 快照便于本地审计和迁移，规模扩大后可以替换为 SQLite FTS5/Chroma/pgvector，但必须保留 generation 和来源字段。
- 固定字符窗口不是最终语言学分块策略，但它能在 M4.2 先验证 100% 偏移回切与失败保留。

## 验证

`tests/integration/test_m4_chunk_retrieval.py` 验证 0006 升降级、Chunk 偏移回切、approved 项目隔离、BM25/Vector 结果字段、运行时文本索引，以及失败重建后旧快照仍可查询。
