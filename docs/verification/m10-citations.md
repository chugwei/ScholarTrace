# M10.2 BibTeX 与章节草稿验收

日期：2026-08-11（Asia/Shanghai）

## 本批次范围

本批次实现离线 BibTeX 解析、常用 Markdown/LaTeX citation key 提取、缺失引用报告、稳定 BibTeX 导出，以及由 SectionContract 和 Claim Ledger 驱动的确定性 Markdown 草稿模板。没有接入网络元数据服务，也没有生成真实论文结论。

## 验收命令与结果

```text
uv run ruff check src tests scripts
All checks passed!

uv run pytest tests/unit/test_m10_citations.py -q
5 passed

uv run python scripts/check.py
Ruff format/check: passed
pytest: 158 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.
```

目标测试覆盖：

- author/title/year/DOI 解析、稳定排序和 BibTeX 重建；
- `[@key]`、`; @key`、`\\citep{key}` 提取以及缺失 key 报告；
- 缺字段 BibTeX 的失败降级；
- SectionContract 缺少 Claim 或 citation 时阻断；
- 草稿保留 Claim 状态、Claim ID 和 citation key，不引入未经来源绑定的数字。

## 边界

Fixture bibliography 只用于离线契约测试；解析成功不等于 DOI、作者、年份或原文已经通过外部真实性核验。M10.3 必须继续验证章节数字和 Claim 与上游证据的一致性。
