# M3 学习日志：独立文献库

M3 的目标是建立一个可能包含噪声的全局文献目录，并把项目候选关联与正式证据分开。M3.1 已验证 Schema、迁移、SHA-256 去重、项目候选关联和目录搜索；PDF 解析、外部元数据查询和失败降级在后续小批次继续完成。

## 为什么需要独立文献库

农业视觉项目常会同时收到合法上传的论文、只有 DOI 的元数据和解析失败的扫描件。文献属于全局目录，不应因为暂时服务某个荔枝病虫害项目就复制一份；项目只保存 `ProjectDocument(status="candidate")`，不能把候选自动当作证据或 approved 文献。

## M3.1 数据流

```text
输入内容 → content_sha256 → stable document_id → documents
                                           └→ project_documents(candidate)
目录搜索 ← searchable 且非 failed 的元数据
```

`Document` 保存来源类型、内容哈希、解析状态、质量状态、标题/作者/年份/DOI/URL 和运行时路径引用。`Document` 的正文不放进 Graph State；`LiteratureRepository` 的短事务保证内容重放幂等。项目关联使用项目和文献双键，跨项目不会泄漏。

## 概念与最小示例

- **Schema** 用 Pydantic 拒绝未知来源类型和错误 SHA-256；它是边界契约，不是外部元数据的真实性证明。
- **Migration** `0004` 创建全局 `documents` 与关系表，按 `0003 → 0004` 升级，降级会同时移除两张目录表。
- **Repository** 负责事务、唯一约束和目录搜索；它不执行网络请求，也不把失败文件返回为检索结果。
- **Storage boundary** 在 M3.2 中由 PDF Library 管理，数据库只保存相对路径；仓库 `.gitignore` 保护全文和运行产物。

```python
document = repository.save_document(document_contract)
candidate = repository.attach_document(project_id, document.document_id)
hits = repository.search_catalog("lychee")
```

重复 `save_document()` 返回原记录；失败状态可以保留用于诊断，但 `search_catalog()` 会排除它。M3.1 使用合成/脱敏条目，不能称为真实论文证据。

## 与前后里程碑的关系

M2 提供项目和人工审批边界，M3 将文献目录作为独立实体加入；M4 才会在项目候选上实现 approved/rejected、Chunk、混合检索和 EvidenceCard。M3 不提前宣称 RAG 或可信证据已实现。

## M3.3 工具调用与降级学习

Crossref/OpenAlex 客户端是确定性工具边界，不是 Graph Node，也不把网络响应直接当作科研结论。`MetadataProvider` 把两个 API 归一化为同一个 `MetadataLookupResult`；`LiteratureMetadataService` 是编排层，按顺序调用 Tool 并保留失败原因。

当 Crossref 返回 503 时，服务可以继续尝试 OpenAlex；当两个服务都不可用时，结果明确为 `unavailable` 且 `metadata=None`。当 API 返回空结果时是 `not_found`，同样不能生成假的 DOI 或作者。只有 `ok` 结果能显式生成 `metadata_only` Document，而且它没有全文路径，不会被误说成论文全文。

```python
service = LiteratureMetadataService([CrossrefClient(), OpenAlexClient()])
bundle = service.lookup("lychee disease detection")
if bundle.status == "ok":
    document = metadata_document_from_lookup(bundle.attempts[-1])
```

CI 使用 `httpx.MockTransport` 验证请求和失败路径，不依赖真实 API Key、网络或付费服务；真实来源仍需在使用时保存响应时间和人工核验记录。M4 才会把项目候选纳入 approved/rejected 和 EvidenceCard。
