# M4.3 EvidenceCard 与引用校验验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m4-evidence-rag`
- 环境：Windows，CPython 3.12.13，SQLite，SQLAlchemy 2
- 数据性质：合成/脱敏农业视觉条目；DOI、URL 和回归文本均为测试输入，不代表真实论文事实

## 已执行命令

```text
uv run pytest tests/integration/test_m4_evidence_cards.py -q
5 passed

uv run ruff format --check src tests scripts
59 files already formatted

uv run ruff check src tests scripts
All checks passed!

uv run python scripts/check.py
pytest: 98 passed in 39.22s
Fixture validation: 3 synthetic project fixtures passed
```

## 覆盖范围

- 0007 `evidence_cards` 迁移可以升级、回退到 0006 并再次升级；
- 未批准的 ProjectDocument 不能创建 EvidenceCard；
- quote 必须存在于 approved Chunk，配置源文本根目录后绝对偏移还必须匹配运行时文本；
- DOI、HTTP(S) URL 和安全相对本地路径的 locator 选择，缺失/不安全来源拒绝；
- 同一证据卡重复提交幂等，冲突内容不覆盖原卡；
- 固定回归文件包含 10 条查询，离线 BM25 + hashing Vector 的 top-1 结果全部命中预设主题。

## 限制

当前只做 locator 格式和本地片段校验，没有访问 Crossref/OpenAlex 验证 DOI 是否真实注册，也没有真实文献授权或人工标注 Top-k 证据。EvidenceCard 的 statement 仍需研究者判断；M4.4 发布审查和 `v0.4.0` 仍未完成。
