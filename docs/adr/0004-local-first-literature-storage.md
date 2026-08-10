# ADR 0004：本地优先且只读的文献全文存储

- 状态：已接受
- 日期：2026-08-11
- 范围：M3.2 PDF 入库

## 背景

文献目录需要知道原始文件和解析文本在哪里，但公开仓库不能保存未经授权的论文全文。解析失败的文件还不能污染目录搜索或被误认为证据。

## 决策

`DocumentLibrary` 只接受调用方明确提供的本地文件路径；先计算 SHA-256，再解析。成功文件原子写入调用方的运行时 storage root，保存后移除写权限，数据库只记录相对路径。失败文件只写入 `failed/parse_failed/searchable=false` 的元数据诊断，不复制原文。运行时目录由 `.gitignore` 覆盖，不能作为公开项目资源。

## 取舍

- M3 先支持合法用户上传；Crossref/OpenAlex 只提供元数据，外部全文下载不在本批次范围。
- 空文本和元数据缺失分别标记为 `empty_text` / `metadata_incomplete`，不靠模型补造标题、作者、年份或 DOI。
- 只读权限降低误写风险，但不替代文件系统 ACL、版权审查或备份策略；部署版再接入对象存储和更细的权限控制。

## 验证

`tests/integration/test_literature_ingestion.py` 覆盖合法 PDF 的去重、pypdf 元数据、只读路径、非法 PDF 的失败隔离和项目 candidate 关联。测试文件为合成 PDF，不是受版权保护的真实论文。
