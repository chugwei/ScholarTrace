# ADR 0015：创新候选只能获得验证入口

- 状态：已接受
- 日期：2026-08-11
- 范围：M6.3 证伪实验、基线/消融与状态门禁

## 背景

先验证据和方法差异可以支持一个值得验证的候选，但不能单独证明原创性或性能收益。系统需要一个不会把候选状态误写成论文贡献的人工门。

## 决策

- 只有 `AlgorithmSpec` 和 `PriorArtMap` 均为 `approved`，候选才可以进入 `approved_for_experiment`。
- 入口前必须保留先验 EvidenceCard、显式差异、预期机制、证伪实验、至少一个基线和至少一个消融。
- `novelty_status=not_novel` 直接阻断；`unverified` 和 `conflicting` 保持可见，后者只能带 warning 进入验证。
- `approved_for_experiment` 的含义是允许安排验证，不是已证明创新。候选可以被 `withdrawn`，而不是删除历史。
- 证伪计划只生成结构化提案，不执行训练、不生成指标、不更新论文 Claim。

## 验证

`tests/integration/test_m6_algorithm_repository.py` 覆盖审批顺序、`not_novel` 阻断、验证入口、撤回和草案拒绝。`build_falsification_plan()` 的输出包含冻结数据划分、基线、消融和可追溯运行要求。
