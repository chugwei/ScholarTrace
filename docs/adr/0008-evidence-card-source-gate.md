# ADR 0008：EvidenceCard 必须绑定可定位来源片段

- 状态：已接受
- 日期：2026-08-11
- 范围：M4.3 可信证据卡与引用回归

## 背景

检索结果只是候选上下文，不能直接成为论文引用或研究结论。没有精确片段、项目批准关系或可解析 locator 时，系统无法区分真实来源和模型补写。

## 决策

EvidenceCard 只能由 `EvidenceCardService` 从项目 `approved` Chunk 创建。服务要求 quote 精确出现在 Chunk 中，保存文档绝对偏移和 SourceSpan，并从格式可验证的 DOI、HTTP(S) URL 或安全相对本地路径中选择 locator。配置运行时文本根目录时，对应原文片段必须再次匹配。EvidenceCard 持久化状态固定为 `verified`，statement 不由系统宣称为已证明结论。

相同项目、Chunk、片段和 statement 使用稳定 ID 幂等保存；来源或片段校验失败不写入数据库。固定回归集只评估离线索引排序，不把合成结果当作真实论文证据。

## 取舍

- locator 语法校验不等于 DOI 已被外部注册机构确认；真实 DOI 解析和授权状态需要后续外部来源核验。
- 先绑定 Chunk 偏移再支持更复杂的页码/版面定位，保证当前文本解析路径可复现。
- EvidenceCard 不替代人工科研判断，也不自动生成 Claim 或论文段落。

## 验证

`tests/integration/test_m4_evidence_cards.py` 覆盖迁移回滚、未批准阻断、quote/运行时文本篡改、locator 选择、幂等和 10 条固定回归查询。
