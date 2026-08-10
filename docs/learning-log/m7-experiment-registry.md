# M7 学习日志：实验计划与结果可信性

M7 从 M6 的“允许验证”入口开始建立实验登记。第一批只冻结计划和矩阵，不把实验意图误写成实验结果。

## 新概念与真实问题

农业视觉实验经常只保存训练日志里的最高值，却没有数据版本、配置、代码提交、环境或随机种子。`ExperimentPlan` 把假设、基线、候选、消融、指标、资源预算、停止条件和失败回退写成可版本化契约；矩阵行进一步固定每种方法的配置、数据版本、种子和重复次数。

## 数据流

```text
M6 approved_for_experiment candidate
        ↓
ExperimentPlan draft + ExperimentMatrix
        ↓ canonical SHA-256 / version parent
human freeze gate
        ↓
frozen ExperimentPlan → M7.2 RunManifest import → M7.3 MetricResult
```

只有 frozen 计划可作为后续 Run 的正式输入。SQLite 0011 保存完整 payload、状态、版本、父计划和审核元数据；draft 重放是幂等的，冻结版本不会被就地改写。

## LangGraph 概念在本里程碑中的位置

- **State** 只需要保存当前 `plan_id` 和下一步，不把矩阵或日志塞进 Graph State。
- **Node/Edge** 后续实验图会用节点导入 manifest、校验产物，用边把完整和不完整 Run 路由到不同处理；本批次先由 Repository 验证不变量。
- **Reducer** 仍只合并轻量的 next actions 或 warning，不聚合指标。
- **Checkpointer** 可恢复人工冻结前后的流程，但不能替代 SQL 中的 frozen 计划版本。
- **`interrupt()` / resume** 沿用 M5 的人工审批模式：冻结前暂停，`Command(resume=...)` 恢复后才写入批准元数据。
- **Subgraph** M7 后续会把计划、导入和重算拆成实验子图；M7.1 不提前执行外部命令。
- **Tool** 是确定性检查和哈希计算；训练、日志解析和指标重算会在后续批次通过显式适配器进入。

## 常见错误与测试

常见错误是没有批准算法就冻结计划、修改冻结计划的内容、重复使用版本号或矩阵中使用重复种子。Schema 和 Repository 测试分别覆盖结构不变量、审批顺序、父版本、幂等和迁移回滚。当前示例是合成/脱敏农业视觉计划，不是实际训练承诺或指标。

M6 提供候选和证伪计划；M7.1 只冻结实验意图，M7.2 将导入现有日志/配置/权重/指标并标记缺失证据，M7.3 再独立重算指标和更新 Claim。M8 才考虑受控执行。

## M7.2 Run Manifest 与指标边界

`RunManifest` 记录 plan/matrix 身份、代码 SHA、数据版本、配置、环境锁、种子、Checkpoint 和相对 Artifact 路径。导入器先验证它引用的是 frozen 计划，再计算缺失字段；缺失时保存 `incomplete` 和 `missing_requirements`，不丢弃失败信息。相对路径检查阻止把私有绝对路径或 `..` 路径带入 Artifact 根目录。

日志和报告中的数值进入 `MetricResult` 时保留 `source=training_log` 或 `imported_report`、`verification_status=unverifiable`、`is_final=false`。这条边界避免“训练日志最高值”自动变成论文最终指标。M7.3 的独立重算必须另有评估脚本 SHA、数据版本和可重复输入，才能产生 verified/final 结果。

## M7.3 重算、汇总与 Claim

`recompute_metric()` 是一个确定性 Tool：输入显式预测和目标，输出 accuracy、MAE 或 RMSE，不执行训练。只有完整 Run 引用的 frozen plan、相同 `data_version` 和评估脚本 SHA 同时满足，Repository 才写入 verified/final `MetricResult`。聚合器只读取这些记录，报告值即使数值更高也不会混入均值或标准差。

Claim 更新是追加的状态事件。如果所有绑定 MetricResult 都 verified/final，请求的 `supported` 或 `contradicted` 才能保留；只要有日志值或缺失结果，状态就降为 `insufficient` 并保存原因。这让“有一个数字”与“有足够证据支持 Claim”在数据模型中分开。
