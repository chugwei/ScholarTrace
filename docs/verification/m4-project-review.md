# M4.1 项目文献审核与相关度验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m4-evidence-rag`
- 环境：Windows，CPython 3.12.13，SQLite，SQLAlchemy 2
- 数据性质：合成/脱敏农业视觉条目，不是真实论文证据

## 已执行命令

```text
uv run ruff format src tests
49 files left unchanged

uv run ruff check src tests scripts
All checks passed!

uv run pytest tests/integration/test_m4_project_document_review.py -q
3 passed

uv run python scripts/check.py
Ruff format: 51 files already formatted
Ruff lint: All checks passed
pytest: 89 passed in 34.29s
Fixture validation: 3 synthetic project fixtures passed
```

## 覆盖范围

- 0005 迁移增加的审核字段可升级、回退到 0004 并再次升级；
- `candidate` 关联按项目隔离，确定性 token overlap 可稳定排序；
- 人工批准/拒绝保存 actor、理由、时间和相关度；
- `list_approved_documents()` 不返回 candidate 或 rejected；
- 失败或不可搜索文献不能批准，空白理由不能提交。

## 限制

本批次尚未实现 Chunk、全文索引、BM25、Vector、Rerank 或 EvidenceCard；排序分数不是语义相关性证明。全量质量门禁已通过，但 M4.1 发布候选的独立环境、分支推送和 CI 状态仍需在提交后记录。外部 API、真实论文和真实场景不在本记录的证据范围内。
