# ADR 0005：外部文献元数据采用可替换客户端与显式降级

- 状态：已接受
- 日期：2026-08-11
- 范围：M3.3 Crossref/OpenAlex 查询

## 背景

文献 DOI、标题和作者可以来自 Crossref 或 OpenAlex，但外部 API 会超时、限流、返回空结果或改变字段结构。CI 不能依赖网络，也绝不能在失败时让模型补造学术元数据。

## 决策

两个客户端实现相同 `MetadataProvider` 协议，返回 `MetadataLookupResult(status, metadata, error)`；编排服务按显式顺序尝试并保留每次 attempts。HTTP/JSON 失败返回 `unavailable`，空结果返回 `not_found`，都不生成 Document。成功元数据可以显式注册为 `metadata_only` Document，来源类型和没有全文路径必须保留。

## 取舍

- 使用 `httpx.MockTransport` 做离线契约测试，不把真实网络绿灯当作 CI 证据；真实 API 可由后续应用层注入 transport、超时和限流策略。
- Crossref/OpenAlex 只提供元数据，项目候选和 EvidenceCard 的批准仍由 M4 负责。
- 不自动下载受版权限制的全文；用户合法上传仍走 M3.2 的本地 PDF 路径。

## 验证

`tests/integration/test_literature_providers.py` 覆盖两家 API 的字段归一化、Crossref 失败后 OpenAlex fallback、连接失败和空查询拒绝。结果只使用 MockTransport 构造的脱敏 JSON。
