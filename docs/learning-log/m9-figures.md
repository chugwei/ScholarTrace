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
