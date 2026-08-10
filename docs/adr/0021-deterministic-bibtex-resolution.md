# ADR 0021：使用确定性 BibTeX 解析和引用解析

- 状态：accepted
- 日期：2026-08-11
- 范围：M10.2 BibTeX 与章节草稿

## 决策

M10.2 使用标准库实现受限、可离线测试的 BibTeX 解析器，要求每个可引用条目具有唯一 key、author、title 和四位 year；解析结果进入 `BibTeXEntry`，Markdown/LaTeX 中的 `[@key]`、`; @key` 和 `\\cite{key}` 通过确定性解析器校验。缺失 key、重复 key、格式错误或不支持的 entry type 都产生失败，而不是调用模型猜测。

章节草稿由 `generate_section_draft()` 根据 `SectionContract`、Claim Ledger 和已解析 bibliography 生成带来源 ID 的 Markdown 模板。它不会计算或编造 MetricResult 数字；缺少必需 Claim 或 citation key 时直接阻断。

## 理由

引用校验是科研真实性门禁，必须能在无网络、无付费 API 的 CI 中重放。受限解析器覆盖 M10 首版所需字段，并把复杂 BibTeX/CSL 转换留给后续可替换 Provider；确定性模板让章节生成可审查，长文本生成仍需人工修订。

## 后续影响

M10.3 将把引用报告、Claim Ledger、MetricResult 和 FigureSpec 连接成章节一致性检查。当前批次不宣称外部 DOI 真实性已验证，真实文献仍必须来自可核验来源。
