# M3.1 独立文献目录验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m3-literature-library`
- 环境：Windows，CPython 3.12.13，SQLAlchemy 2.x

## 验证命令与结果

```text
uv run pytest tests/integration/test_literature_repository.py -q
3 passed

uv run ruff format --check src tests scripts
46 files already formatted

uv run ruff check src tests scripts
All checks passed
```

## 覆盖内容

- `0004` 迁移创建 `documents` / `project_documents`，可降级到 `0003` 后再次升级；
- 相同内容 SHA-256 重放不新增 Document；不同项目可独立建立 candidate 关联；
- 目录搜索只返回 searchable 且非 failed 的元数据；失败条目保留诊断记录但不污染索引；
- Document Schema 拒绝未知 source_type 和非法内容哈希；
- 文献目录与 M2 项目实体使用同一业务数据库但通过独立 Repository 边界访问。

## 限制

本批次尚未实现 PDF 解析、Crossref/OpenAlex 查询和全文只读保存；M3.2/M3.3 会分别加入并提供离线降级测试。条目使用合成/脱敏数据，不代表真实文献检索结果。
