# M5 学习日志：管线与数据采集设计

M5 把 M4 的文献证据边界连接到可执行的研究方案。M5.1 先建立两个结构化、可版本化的契约：`PipelineSpec` 描述数据/训练/评估/交付阶段，`DataCollectionProtocol` 描述采样、采集字段、标注、划分和泄漏控制。它们目前只是持久化设计记录，不能被描述成已经执行的采集或实验。

## M5.1 的真实问题

荔枝病虫害项目如果只保存一段 Markdown，很难知道“按哪个版本采集、怎样划分、如何防止同一果园泄漏到测试集”。PipelineSpec 用有序 stage 记录输入/输出，DataCollectionProtocol 用 capture fields 和 leakage controls 记录可检查约束。每次结构改变都会产生新版本，批准版本不会被覆盖。

## 数据流

```text
研究问题 + approved EvidenceCard
        ↓ 研究者提交 draft
PipelineSpec / DataCollectionProtocol
        ↓ canonical payload → content_sha256
DesignRepository(SQLite 0008)
        ↓ 人工批准
approved → superseded（旧版本）
```

最小示例：

```python
spec = repository.save_pipeline(pipeline_draft)
approved = repository.approve_pipeline(
    "lychee-m5", spec.pipeline_id, "researcher-001", "黄金样例结构完整"
)
protocol = repository.save_protocol(protocol_draft)
```

相同内容重放返回相同记录；已批准版本修改必须指定 `parent_pipeline_id` 或 `parent_protocol_id`，并使用下一版本号。数据库保存完整 JSON payload，同时把状态、哈希和批准元数据放在可查询列中。

## 概念边界

- **Schema**：验证阶段/采集字段、唯一名称和必填约束，不证明数据已经采集。
- **Repository**：事务、版本、哈希和批准状态的持久化边界，不是执行训练或采集的 Tool。
- **State**：M5.2 Subgraph 才会把当前 design ID 放入轻量 Graph State；当前批次不把整个方案塞入 State。
- **Node/Edge**：M5.2 将用 Node 生成/校验候选，用 Edge 路由人工批准；M5.1 不提前创建空图。
- **Checkpointer**：记录设计工作流快照，不能替代 SQLite 中的版本和批准审计。

## 常见错误与测试

常见错误是直接编辑已批准方案、重复 stage/field 名称或把同一场景同时放进 inclusion/exclusion。Schema 测试拒绝这些结构；Repository 测试验证 0008 升降级、幂等保存、项目隔离、批准/拒绝和显式父版本。所有样例是合成/脱敏的农业视觉描述，不是用户真实采集授权。

M4 提供 approved 文献和 EvidenceCard 来源链；M5.1 把它们作为研究设计输入。M5.2 将增加 Subgraph 与流程图，M5.3 增加质量/泄漏执行检查，M5.4 再导出并发布 v0.5.0。

## M5.3 质量门禁与比较

质量检查的目标是阻止明显不可审计的设计进入批准状态，而不是替研究者做出科研判断。PipelineSpec 检查相邻阶段的输入/输出是否连通；DataCollectionProtocol 检查划分和泄漏控制是否明确说明分组、会话、来源、主体或重复边界。每个 finding 有稳定 code、severity、message 和 path，可在 UI 或导出中展示。

版本比较忽略审核时间等元数据，只报告真正改变的字段以及新增/删除的 stage ID。例如在荔枝方案中增加 `report` 阶段会得到 `changed_fields=["stages"]` 和 `added_stage_ids=["report"]`。报告描述结构差异，不证明数据已经通过质量检查；真实采集后仍需要样本级验证。

批准流程先生成完整 `DesignValidationReport`，有 error 就抛出 `DesignValidationError`，事务保持两个草案状态且不写批准审计。通过后由 `approve_design_pair()` 在一个事务中批准两个契约，避免管线已批准而采集协议仍是草案。

## M5.4 导出与发布边界

导出器把“已批准的结构化方案”和“仅供编辑的草案”明确分开：`export_design_bundle()` 在写文件前检查两个 status 都是 `approved`，并在 Markdown/YAML 中保留版本、父 ID、审核者和 canonical SHA-256。这样导出的 YAML 可以被下游工具重读，Markdown 可供研究者审查；两者都不伪称采集或实验已经发生。

同一输入重复导出字节一致，临时文件替换避免部分结果。M5 的学习链路从 M4 approved EvidenceCard 开始，经 M5.1 Schema、M5.2 Subgraph、M5.3 质量/泄漏门禁到 M5.4 正式方案快照；M6 才消费批准方案生成算法与创新候选。
