# ADR 0022：用显式标记做论文数字回溯

- 状态：accepted
- 日期：2026-08-11
- 范围：M10.3 章节一致性与证据缺口

## 决策

论文草稿中的可验证事实使用两个机器可读标记：`{{claim:claim-id}}` 绑定 Claim Ledger，`{{metric:metric-id value=0.9}}` 绑定 verified/final MetricResult。`validate_manuscript_consistency()` 检查标记是否存在上游记录、渲染值是否等于 MetricResult，并比较 Abstract、Results、Conclusion 中同一 metric ID 的值。Conclusion 中未在 Abstract 或 Results 出现的 Claim 会单独列为新 Claim。

## 理由

从自然语言段落猜测所有数字会把年份、样本量和指标混在一起，也可能掩盖模型补写。显式标记让生成器、人工修订和审查工具共享同一追溯协议；普通文字仍可由人审查，但不能作为正式结果数字的唯一来源。

## 后续影响

M10.4 发布候选必须将一致性报告加入验收。M11 Web 编辑器需要保留这些标记或提供等价的结构化编辑；导出到投稿格式时应保存原始 Markdown 和来源清单。
