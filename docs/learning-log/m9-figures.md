# M9 学习日志：可复现图表系统

M9 把 M7 的 verified MetricResult 接入可重建的图表 Artifact Bundle。M9.1 只固定 FigureSpec、输入点和 provenance 门禁，绘图脚本与视觉检查在后续批次实现。

## 新概念与真实问题

论文图表常被当成一次性 PNG，删除后无法知道数据、脚本或坐标设置。`FigureSpec` 将图表类型、标题、坐标轴、数据版本、输入点、引用的 MetricResult、输出格式和 caption 写成可哈希契约。`FigureRepository` 只接受同一项目中 `verified` 且 `is_final` 的 MetricResult，并检查 data_version 一致；训练日志临时值不能进入正式结果图。

## 数据流

```text
verified/final MetricResult
        ↓ project + data_version gate
FigureSpec draft + content SHA-256
        ↓ human approval
figure bundle (input-data.csv + generate_figure.py + PNG/SVG/PDF + provenance)
```

M9.1 的 SQLite 0017 只保存 FigureSpec 设计和状态。真正的文件 Artifact 会在 M9.2 由确定性脚本生成，M9.3 再校验文件中的数字与 MetricResult 一致。

## LangGraph 概念在本里程碑中的位置

- **State** 可保存当前 `figure_id` 和审批动作，不保存二进制图像。
- **Node/Edge** 后续按 draft → validate → render → check → approve → publish 路由。
- **Reducer** 只合并有序诊断消息，不能合并或修改指标数值。
- **Checkpointer** 保存人工审批暂停点；FigureSpec 的 SQL 版本和内容哈希才是事实来源。
- **interrupt/resume** 将用于发布图表前的人审；M9.1 尚未启动图表发布图。
- **Subgraph** 可把建议、绘图、数值检查和视觉验收隔离，避免图表脚本绕过 provenance。
- **Tool** 是 CSV 校验、哈希、绘图和数值比较；图表结果不能反向制造 MetricResult。

当前示例仍是合成/脱敏农业视觉指标，不是实际论文图或真实场景结果。

## M9.2：Artifact Bundle 与脚本重建

`FigureRenderer` 先把输入点写为确定性 CSV，再生成只依赖 bundle 内 CSV 的 `generate_figure.py`。渲染器使用 Matplotlib `Agg` 后端，避免 GUI 状态影响 CI，并输出 FigureSpec 要求的 PNG、SVG 和 PDF。`provenance.json` 保存 data/script SHA-256、data_version 和 MetricResult IDs；Bundle 通过临时目录改名发布，避免半成品目录被当成正式图表。

删除三个图像文件后，测试重新运行 bundle 脚本并恢复所有输出，输入 CSV hash 保持不变。这证明的是可重建性，不是视觉质量或真实科研结论；M9.3 还要检查图中数值与 MetricResult 一致，M9.4 才做人工视觉验收。

## M9.3：建议、Caption 和数值门禁

`recommend_figure_types()` 只接收 verified/final MetricResult；没有验证结果时返回空建议，避免把训练日志或猜测变成图。`build_caption()` 明确列出 MetricResult IDs 和 data_version，不引入因果或性能结论。`validate_bundle_numeric_consistency()` 同时读取 CSV、FigureSpec、MetricResult 和 provenance.json，检查每个 label/value、data/script SHA-256 和 metric IDs；任何篡改都会形成 failed 报告。

M9.3 仍不等于视觉验收：数值报告通过只能说明数据链一致，不能证明坐标、字体、图例和布局适合论文。M9.4 将实际打开生成图并记录视觉证据。
