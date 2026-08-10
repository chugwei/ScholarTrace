# M10.1 Manuscript 契约验收

日期：2026-08-11（Asia/Shanghai）

## 本批次范围

本批次实现 Manuscript、Section Contract、Claim Ledger 三个结构化契约，SQLite 0018 迁移，以及项目隔离的 `ManuscriptRepository`。没有生成论文正文、BibTeX 或引用结论。

## 验收命令

```text
uv run ruff format src tests scripts
1 file left unchanged

uv run ruff check src tests scripts
All checks passed!

uv run pytest tests/integration/test_m10_manuscript_repository.py -q
4 passed
```

目标测试覆盖：

- 0018 `upgrade → downgrade 0017 → upgrade`，三张 M10 表按依赖逆序回滚；
- Manuscript 首版本、父版本、内容幂等和项目隔离；
- SectionContract 保存、引用列表和 Conclusion 新 Claim 禁止；
- Claim 的 `insufficient` 降级、validated Run/verified final MetricResult 支持和缺失指标拒绝。

## 边界

测试数据是合成/脱敏农业视觉数据。通过只表示论文事实的结构化来源边界已建立，不表示真实文献、真实实验结果或已经生成可投稿论文。
