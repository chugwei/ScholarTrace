# M6 学习日志：算法设计与创新候选

M6 的第一批把 M4 的 `EvidenceCard` 和 M5 的批准设计连接到算法设计记录。这里的“创新”只表示一个需要实验验证的候选，不表示原创性已经成立。

## 新概念与真实问题

农业视觉项目经常把“换一个模块”直接写成创新。`AlgorithmSpec` 先描述任务、输入输出、组件、训练目标、推理策略、评估协议以及所依赖的管线和采集协议；`PriorArtMap` 再为每条先验工作记录 EvidenceCard、方法摘要、已报告的限制和适用范围。这样可以把工程改进、性能调优、算法组合和待验证方法差异分开保存。

## 数据如何流动

```text
M4 approved EvidenceCard
        + M5 approved PipelineSpec/DataCollectionProtocol
        ↓
AlgorithmSpec draft → canonical SHA-256 → 人工批准
        ↓
PriorArtMap draft（每条记录绑定 EvidenceCard）→ 人工批准
        ↓
M6.2 InnovationCandidate（差异、机制、证伪实验）
```

SQLite 0009 将完整结构化 payload 与可查询的状态、版本、父 ID、哈希和批准元数据分开保存。相同 canonical 内容重放返回同一记录；已批准版本必须以父版本和递增版本号创建新记录。审批缺失的 EvidenceCard 会失败，而不会把一个看似合理的先验条目变成正式证据。

## 最小运行示例

```python
algorithm = repository.save_algorithm(algorithm_draft)
approved_algorithm = repository.approve_algorithm(
    "lychee-m6", algorithm.algorithm_id, "researcher-001", "证据和设计引用已核对"
)
prior_art = repository.save_prior_art_map(prior_art_map_draft)
approved_map = repository.approve_prior_art_map(
    "lychee-m6", prior_art.map_id, "researcher-001", "先验工作逐条复核"
)
```

示例中的项目和 EvidenceCard 是合成/脱敏测试数据，不是真实论文结论。正式项目必须把 ID 绑定到 M4 的真实、可定位来源。

## LangGraph 概念在本项目中的位置

- **State** 只保存当前阶段和实体 ID，不保存 PDF 或长算法说明；M1 的 `ResearchProjectState` 是这一边界的实际代码。
- **Node** 执行一个状态转换，例如 M5 研究设计图中的 draft 持久化节点；M6.1 的 Repository 本身是确定性持久化工具，不是假装成 Agent。
- **Edge** 决定下一步，例如 M5 中审批前后边界；M6.3 会把证据门禁接到候选审批路径。
- **Reducer** 合并消息或下一步列表，避免重放重复追加；它不负责判断算法是否原创。
- **Checkpointer** 保存 Graph 的可恢复快照，不能替代 0009 中可查询的算法版本历史。
- **`interrupt()` / resume** 在 M5 的人工审批 Subgraph 中暂停草案；恢复后使用 `Command(resume=...)` 继续，审批结果仍由 Repository 原子写入。
- **Subgraph** 是领域流程的组合边界。M5 的研究设计 Subgraph 将被 M6 的算法候选流程复用，但 M6.1 不提前创建空的多 Agent 系统。
- **Tool** 是确定性能力，例如 SHA-256、EvidenceCard 存在性查询和迁移；工具不会自行生成论文 Claim。

## 常见错误与测试

常见错误包括重复使用同一版本号、修改已批准记录、把不存在的 EvidenceCard ID 当作文献依据以及在算法尚未批准时批准先验地图。集成测试覆盖这些失败路径、数据库回滚、幂等保存和项目隔离。`unresolved_search_gaps` 只产生 warning，提醒继续检索，不会输出“没有先验工作”。

M5 提供批准的管线和采集协议；M6.1 只建立算法和先验工作契约，M6.2 将增加方法差异和创新候选，M6.3 再增加证伪、基线/消融和“仅可进入实验”的状态门禁，M7 才能把候选接入实验计划与结果导入。

## M6.2 候选与差异表

`InnovationCandidate` 将一个候选拆成先验条目、EvidenceCard ID、方法差异、识别出的 gap、提议改动、预期机制、预期收益和风险。`MethodDifference` 要明确“先验方法做什么、候选改变什么、预期影响是什么”，避免只写“效果更好”。候选保存前会检查它引用的条目确实属于对应的 `PriorArtMap`，并检查证据 ID 属于当前项目。

候选的完整度排序是可重复的审查队列：证据引用、差异、机制、证伪实验、基线和消融分别贡献固定权重；同分按 ID 稳定排序。这个分数不表示原创性，也不替代人工决定。候选在后续审批前保持 `draft` 和 `novelty_status=unverified`。

最小数据流为：`approved PriorArtMap → InnovationCandidate draft → completeness ranking → M6.3 experiment gate`。M6.3 才会允许一个候选进入实验计划，且状态名称会明确是“允许验证”，不是“已证明创新”。

## M6.3 证伪与状态门禁

`build_falsification_plan()` 只把候选的机制、证伪描述、基线和消融整理成提案，并附带固定的数据划分、对照报告和运行溯源要求。它不启动命令，也不产生 MetricResult。`approve_candidate_for_experiment()` 在一个事务中检查算法规格和先验地图已批准、证据仍属于项目且候选没有标记 `not_novel`，然后把状态改为 `approved_for_experiment`。这个名称刻意描述“可以验证”，不描述科学结论。

如果先验工作发生冲突，候选仍保留 `conflicting` 和 warning，供研究者判断；如果确认已有工作覆盖，`not_novel` 会被门禁阻断。已进入验证的候选可以记录撤回原因，历史仍可查询。M7 将消费这个入口来冻结实验计划，但本里程碑不提前创建实验结果。
