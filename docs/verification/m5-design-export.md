# M5.4 研究设计 Markdown/YAML 导出验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m5-pipeline-data-design`
- 环境：Windows，CPython 3.12.13，PyYAML 6，SQLite
- 数据性质：合成/脱敏农业视觉方案，不是真实采集协议

## 已执行命令

```text
uv run pytest tests/integration/test_m5_design_export.py -q
2 passed

uv run ruff format --check src tests scripts
71 files already formatted

uv run ruff check src tests scripts
All checks passed!

uv run python scripts/check.py
pytest: 111 passed in 46.39s
Fixture validation: 3 synthetic project fixtures passed
```

## 覆盖范围

- draft 设计不能进入正式导出目录；
- approved、同项目的 PipelineSpec/DataCollectionProtocol 同时导出 Markdown 和 YAML；
- YAML 可重新解析，保留 approved 状态和 content SHA-256；
- 中文标题和阶段信息保留，重复导出字节一致；
- 版本比较 Markdown 保留 changed fields、added/removed stages。

## 限制

导出只证明结构化方案快照可读、可重放，不证明数据已采集、授权已取得或质量检查覆盖真实样本。M5.4 发布候选仍需独立 wheel、迁移、main 合并和 `v0.5.0` Tag 验收。
