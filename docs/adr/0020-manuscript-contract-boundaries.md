# ADR 0020：论文契约与 Claim Ledger 的证据边界

- 状态：accepted
- 日期：2026-08-11
- 范围：M10.1 Manuscript、Section Contract、Claim Ledger

## 决策

论文对象先保存版本化契约和来源引用，不在数据库中把模型生成的长文本当作科研事实。`manuscripts` 保存项目、版本、父版本、模板和状态；`section_contracts` 保存章节目标及必须满足的 Claim、EvidenceCard、MetricResult 和 FigureSpec 引用；`claim_ledger` 保存每条重要陈述的类型、状态和来源 ID。可变内容放进 JSON payload，身份、版本、状态、哈希和项目隔离字段使用独立列。

新的 Manuscript 和 Section Contract 从 `draft` 开始。Claim 可以处于 `planned` 或 `insufficient`，但只有在引用项目内的 EvidenceCard、validated Run 或 verified/final MetricResult 后才能标记为 `supported`。`result` 类型的 supported Claim 必须至少绑定一个 MetricResult；没有证据的陈述不会被 Repository 自动升级。

## 理由

论文章节会随着人工修订和证据变化产生版本。独立列提供可查询的版本和隔离门禁，JSON payload 保留契约扩展性；Claim Ledger 与已有 MetricResult/EvidenceCard 的 ID 绑定，避免把草稿文字当成结果。0018 的 downgrade 按依赖逆序删除三张表，保持迁移可回滚。

## 后续影响

M10.2 将在这些契约上增加 BibTeX 和引用解析；M10.3 增加章节一致性、数字回溯和缺失证据报告。当前批次不生成论文正文，也不证明真实农业实验结论。
