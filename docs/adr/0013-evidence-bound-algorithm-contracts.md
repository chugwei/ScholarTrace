# ADR 0013：算法规格与先验工作地图使用证据绑定

- 状态：已接受
- 日期：2026-08-11
- 范围：M6.1 AlgorithmSpec/PriorArtMap

## 背景

算法候选如果只保存一段描述，无法区分已有方法、工程调参和待验证的研究差异。M4 已经提供了项目级 `EvidenceCard`，M5 已经提供了批准的数据与管线设计；M6 需要把这两类输入连接到可复核的算法设计。

## 决策

- `AlgorithmSpec` 和 `PriorArtMap` 都采用版本化结构化契约、canonical SHA-256 和不可覆盖的历史记录。
- `AlgorithmSpec` 必须引用项目中的 `EvidenceCard` ID，并指向已确定的 PipelineSpec 与 DataCollectionProtocol ID。
- `PriorArtMap` 的每一条先验工作记录必须包含至少一个 EvidenceCard ID；审批时检查这些 ID 确实属于当前项目。
- 先批准算法规格，再批准先验工作地图；旧批准版本转为 `superseded`，不删除历史。
- 未解决的检索空缺只产生可见 warning，不能被解释为创新成立或先验工作不存在。

## 取舍

将证据 ID 作为引用而不是复制长文本，可以保持文献来源的单一事实源，并避免把未经验证的作者、DOI 或原文片段写入算法记录。代价是没有 M4 EvidenceCard 时不能批准 M6 设计；这是科研真实性门禁，而不是可选的便利路径。

## 验证

`tests/integration/test_m6_algorithm_repository.py` 覆盖 0009 升降级、幂等保存、版本父链、项目隔离、缺失 EvidenceCard 阻断以及算法/先验地图的审批顺序。
