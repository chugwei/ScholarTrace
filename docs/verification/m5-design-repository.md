# M5.1 研究设计契约与 Repository 验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m5-pipeline-data-design`
- 环境：Windows，CPython 3.12.13，SQLite，SQLAlchemy 2
- 数据性质：合成/脱敏农业视觉方案，不是真实采集协议或现场数据

## 已执行命令

```text
uv run pytest tests/integration/test_m5_design_repository.py -q
4 passed

uv run ruff format --check src tests scripts
63 files already formatted

uv run ruff check src tests scripts
All checks passed!

uv run python scripts/check.py
pytest: 102 passed in 54.17s
Fixture validation: 3 synthetic project fixtures passed
```

## 覆盖范围

- 0008 `pipeline_specs` / `data_collection_protocols` 迁移可升级、回退到 0007 并再次升级；
- PipelineSpec 阶段名和 DataCollectionProtocol 采集字段名唯一，采集 inclusion/exclusion 不得重叠；
- 相同内容重放幂等，canonical SHA-256 持久化；
- draft → approved/rejected 状态门禁、批准者/理由/时间和旧版本 superseded；
- 已批准版本修改必须使用递增版本号和当前批准父 ID；
- 两个项目的方案记录互相隔离。

## 限制

M5.1 还没有 Subgraph、流程图、实际数据质量/泄漏扫描、Markdown/YAML 导出或真实采集。合成方案只证明 Schema、事务和生命周期契约，不证明任何数据采集伦理、授权或研究结果。
