# M8 学习日志：受控执行与排错

M8 从 M7 的“只导入并验证已有产物”进入受控执行。M8.1 先固定执行契约和沙箱边界，实际进程生命周期与排错链路在后续批次实现。

## 新概念与真实问题

农业视觉训练可能需要长时间运行、较大的内存和 GPU 外部环境。研究工作台不能把任意字符串直接交给 shell，也不能让一次失败覆盖已登记的权重或指标。`ControlledRunSpec` 将 frozen plan、矩阵行、argv、后端、相对工作区、资源上限和环境写成可校验请求；`ControlledRunRepository` 只允许它进入 frozen 计划并以 `queued` 身份持久化。

## 数据流

```text
frozen ExperimentPlan + matrix entry
        ↓
ControlledRunSpec (argv + limits + relative paths)
        ↓ policy validation / command SHA-256
SQLite controlled_runs(status=queued)
        ↓ M8.2
per-run staging → controlled process → logs/status → verified artifact publication
```

输入和正式产物不直接暴露给执行进程。Docker 命令构造使用无网络、只读工作区和独立输出卷；本地后端也必须遵守 argv 和相对路径约束。

## LangGraph 概念在本里程碑中的位置

- **State** 后续只保存 execution ID、当前状态和待处理事件，不承载完整日志。
- **Node/Edge** 将按 queued/running/failed/cancelled/timed_out 路由；M8.1 先由 Repository 固定 queued 边界。
- **Reducer** 适合对流式日志按序追加并限制大小，不能静默丢弃截断标记。
- **Checkpointer** 可恢复人工批准或排错流程，但不能代替受控进程的真实状态。
- **interrupt/resume** 将用于修复应用前的人工审批；当前批次尚未应用修复。
- **Subgraph** 可将运行、采集日志、诊断和回归分开，避免排错节点直接修改正式产物。
- **Tool** 是命令校验、哈希和确定性诊断；未验证的外部命令输出不能直接成为科研 Claim。

## 最小示例与常见错误

一个最小请求使用 `["python", "-m", "pytest", "-q"]`，绑定一个已冻结的农业视觉 Fixture 计划。`CommandPolicy` 会拒绝 `python -c ...`、shell 元字符和未列入白名单的模块；路径契约会拒绝绝对路径和 `..` 逃逸。Docker 不可用时只能验证构造出的 argv，不能把构造测试描述为真实容器执行。

M8.1 与 M7 的关系是把可导入的 Run 身份扩展为可排队的受控执行身份；与 M8.2 的关系是为启动、取消、超时和日志提供不可变请求及资源上限。当前所有示例仍是合成/脱敏 Fixture，不是真实训练或现场结果。
