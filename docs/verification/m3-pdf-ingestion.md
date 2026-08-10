# M3.2 PDF 入库与质量标记验证记录

- 日期：2026-08-11（Asia/Shanghai）
- 分支：`feat/m3-literature-library`
- 环境：Windows，CPython 3.12.13，pypdf 6.15.0

## 验证命令与结果

```text
uv run pytest tests/integration/test_literature_ingestion.py -q
3 passed

uv run ruff format --check src tests scripts
46 files already formatted

uv run python scripts/check.py
Ruff lint: All checks passed
pytest: 82 passed
Fixture validation: 3 synthetic fixtures passed
```

## 覆盖内容

- 合法合成 PDF 通过 pypdf 读取标题、作者和创建年份；
- 相同字节从两个路径上传只产生一个 Document 和一份运行时 PDF；
- PDF 与提取文本写到 storage root 的相对路径，并设置只读权限；
- 空文本、元数据缺失分别标记质量状态，不被描述成有正文证据；
- 非 PDF/解析失败文件只保存 failed 诊断，不复制原文，不进入目录搜索；
- 合法文献与项目只建立 `candidate` 关联，不自动变成 approved 或 EvidenceCard。

本批次使用合成 PDF 和离线临时目录，不能证明版权授权、真实文献质量或现场场景效果。M3.3 将加入 Crossref/OpenAlex 可替换客户端和网络失败降级。
