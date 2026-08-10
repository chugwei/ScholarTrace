# M4.2 Chunk 与混合检索验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m4-evidence-rag`
- 环境：Windows，CPython 3.12.13，SQLite，SQLAlchemy 2
- 数据性质：合成/脱敏农业视觉条目，不是真实论文或召回基线

## 已执行命令

```text
uv run pytest tests/integration/test_m4_chunk_retrieval.py -q
4 passed

uv run ruff format --check src tests scripts
55 files already formatted

uv run ruff check src tests scripts
All checks passed!

uv run python scripts/check.py
pytest: 93 passed in 35.96s
Fixture validation: 3 synthetic project fixtures passed
```

## 覆盖范围

- 0006 `document_chunks` 迁移可升级、回退到 0005 并再次升级；
- 固定窗口 Chunk 的字符偏移可以 100% 回切到原始文本，数据库替换可重放；
- `rebuild_project()` 只索引项目 `approved` 文献，不索引 candidate 文献；
- 搜索结果同时返回 BM25 分数、Vector 分数、生成号和完整 Chunk 来源字段；
- `DocumentLibrary` 能从运行时文本生成 Chunk；
- Vector provider 失败时 active 索引文件字节不变，旧 generation 仍可查询。

## 限制

默认 hashing vector 是确定性测试替身，不证明语义相似度、真实论文 Top-k 召回或外部 embedding 服务可用。M4.3 仍需 EvidenceCard、DOI/URL/片段校验和固定 10–20 条检索回归集；本记录没有真实文献或现场数据证据。
