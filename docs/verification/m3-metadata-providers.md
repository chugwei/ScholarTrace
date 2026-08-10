# M3.3 Crossref/OpenAlex 元数据验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m3-literature-library`
- 环境：Windows，CPython 3.12.13，httpx 0.28.1

## 验证命令与结果

```text
uv run pytest tests/integration/test_literature_providers.py -q
4 passed

uv run ruff format --check src tests scripts
48 files already formatted

uv run python scripts/check.py
Ruff lint: All checks passed
pytest: 86 passed
Fixture validation: 3 synthetic fixtures passed

uv run ruff check src tests scripts
All checks passed
```

## 覆盖内容

- Crossref 结果的标题、作者、年份、DOI、URL 和摘要字段归一化；
- OpenAlex 结果的作者、年份、DOI、landing page 和 inverted index 摘要重建；
- Crossref 503 后按顺序 fallback 到 OpenAlex，并保留两个 attempt；
- 连接异常、空结果和空白 query 有确定性降级，不会创建伪造 Document；
- 成功元数据可显式转换为无全文路径的 `metadata_only` Document，保留 provider 来源。

所有响应由 `httpx.MockTransport` 提供，未访问真实 Crossref/OpenAlex；这证明客户端契约和失败行为，不证明外部服务当前可用或任何具体论文事实。
