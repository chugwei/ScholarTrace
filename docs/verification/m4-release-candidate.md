# M4 v0.4.0 发布候选审查

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m4-evidence-rag`
- 目标版本：`v0.4.0`
- 环境：Windows，CPython 3.12.13，uv、Ruff、pytest、Docker 可用

## 范围审查

发布候选包含 M4.1–M4.3：项目级 candidate/approved/rejected 审核、确定性候选相关度、0005–0007 迁移、偏移保真的 DocumentChunk、BM25 + 可替换 Vector、原子索引重建、EvidenceCard、DOI/URL/本地 locator 与原文片段校验，以及 10 条离线检索回归。M5–M12 的管线、实验、论文、Web 和部署能力不在本版本声明范围内。

独立 diff 审查确认：

- 变更集中在文献 Schema、Repository、Chunk/检索/EvidenceCard 服务、0005–0007 迁移、M4 测试和公开工程文档；
- 没有加入计划、Prompt、`AGENTS.md`、`docs/goal-progress.md`、Token、Cookie、数据库、私有论文全文、模型权重或大型运行产物；
- `git diff origin/main...HEAD --check` 无空白错误，秘密/个人路径扫描为 0，tracked 文件大于 5MB 为 0；
- candidate/rejected 不进入项目索引，未批准 Chunk 不可创建 EvidenceCard，失败重建不覆盖旧索引；
- M0–M3 既有测试、迁移回滚、CLI 和许可证声明保持通过。

## 实际门禁

```text
uv run python scripts/check.py
Ruff format: 59 files already formatted
Ruff lint: All checks passed
pytest: 98 passed in 40.30s
Fixture validation: 3 synthetic project fixtures passed

uv build --out-dir .verification/m4-rc-dist
scholartrace-0.4.0.tar.gz
scholartrace-0.4.0-py3-none-any.whl

隔离 venv wheel 安装/import/CLI/迁移
version 0.4.0; __version__ 0.4.0; License-Expression Apache-2.0
scholartrace --help passed
migration 0007

Docker actionlint
server 28.3.2; no diagnostics
```

wheel 中的许可证文件和 `License-Expression=Apache-2.0` 已由独立环境检查；GitHub Actions API 当前若返回 rate limit，CI 状态保持“未验证”，不猜测通过。

Tag 只在该候选提交推送、合并 `main`、main smoke test 和远端 Ref 核验后创建。当前文档记录的是候选，不是已经发布的 Tag。

## 能力边界

回归查询、DOI/URL、文本和农业项目均为合成/脱敏离线输入。locator 格式校验不等于 DOI 已在外部注册机构存在，hashing Vector 不等于语义召回模型；本候选没有真实论文授权、真实文献 Top-k 或真实场景证据。
