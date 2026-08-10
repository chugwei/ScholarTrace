# M3 v0.3.0 发布候选审查

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m3-literature-library`
- 目标版本：`v0.3.0`
- 环境：Windows，CPython 3.12.13，uv、Ruff、pytest、Docker 可用

## 范围审查

发布候选包含 M3.1–M3.3：独立 Document/ProjectDocument 目录、SHA-256 去重、项目 candidate 关联、合法 PDF 入库、pypdf 元数据/文本质量标记、Crossref/OpenAlex 元数据客户端和明确网络失败降级。M4 项目文献 approved/rejected、Chunk、BM25/Vector、Rerank、EvidenceCard 和引用校验不在本版本声明范围内。

独立 diff 审查确认：

- 变更集中在 `src/scholartrace/literature/`、文献 Schema/Repository、0004 迁移、M3 测试和公开工程文档；
- 没有加入计划、Prompt、`AGENTS.md`、`docs/goal-progress.md`、Token、Cookie、数据库、私有论文全文、模型权重或大型运行产物；
- `git diff main...HEAD --check` 无空白错误，秘密/个人路径扫描为 0，tracked 文件大于 5MB 为 0；
- 失败 PDF 不复制到 storage，不进入目录搜索；外部 API 失败不生成 Document 或虚构元数据；
- M0–M2 既有测试和 CLI/Checkpoint 恢复路径保持通过。

## 实际门禁

```text
uv run python scripts/check.py
Ruff format: 48 files already formatted
Ruff lint: All checks passed
pytest: 86 passed
Fixture validation: 3 synthetic fixtures passed

uv run pytest tests/integration/test_literature_repository.py tests/integration/test_literature_ingestion.py tests/integration/test_literature_providers.py -q
10 passed

uv build
sdist and wheel built successfully; package version 0.3.0

独立 wheel venv 安装/import/CLI/迁移
version 0.3.0; scholartrace --help passed; migration 0004 passed
```

`docker run --rm -v <workspace>:/repo -w /repo rhysd/actionlint:latest` 已通过且无诊断；tracked secret/personal-path scan 为 0 matches，tracked 文件大于 5MB 为 0。GitHub Actions API 若因 rate limit 无法读取，保持未验证，不猜测 CI 结论。Tag 只在功能分支推送、合并 `main`、main smoke test 和远端 Ref 核验后创建。

## 能力边界

PDF 和 API 测试使用合成内容、MockTransport 和离线临时目录；它们证明的是文件处理、来源标记和失败契约，不是具体真实论文事实、版权授权或真实农业场景验证。M4–M12 仍需按路线实现。
