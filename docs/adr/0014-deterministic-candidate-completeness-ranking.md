# ADR 0014：候选排序只衡量可审计完整度

- 状态：已接受
- 日期：2026-08-11
- 范围：M6.2 InnovationCandidate 与方法差异表

## 背景

M6 需要在多个候选都具备证据、差异和实验入口时给出可重复的审查顺序。一个分数如果被解释成“创新程度”，会把结构完整性误写成科学结论。

## 决策

`rank_innovation_candidates()` 只根据 EvidenceCard 引用数量、显式方法差异、预期机制、证伪实验、基线和消融条目计算确定性完整度分数。分数相同时按 `candidate_id` 排序，结果附带明确的“不是创新证明”说明。`InnovationCandidate.novelty_status` 保持 `unverified`，除非后续有可核验的文献、实验和人工判断。

## 取舍

排序可以让研究者先审查材料更完整的候选，但不能替代先验检索、实验设计或领域判断。故意不加入模型置信度、不可复现的外部 API 评分或未经来源验证的“新颖度”字段。

## 验证

`tests/integration/test_m6_algorithm_repository.py` 验证候选引用门禁、版本父链、重复保存和排序稳定性；排序结果只用于审查队列。
