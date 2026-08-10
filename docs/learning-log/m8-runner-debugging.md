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

## M8.2：生命周期、日志和产物发布

`RunExecutor` 使用线程池调度受控进程，但进程本身始终由 `subprocess.Popen(..., shell=False)` 以 argv 启动。每次运行有独立 staging 目录和最小环境；输出先写 staging，只有退出码为 0 且正式目标不存在时才复制到临时发布目录并原子改名。失败、取消、超时和日志超限都会留下 staging 与日志，正式 Artifact 不会被覆盖。

日志读取线程把 stdout 分块放入队列，主循环同时检查取消事件和 deadline，因此无输出的长进程也能被超时终止。每个事件带有单调 sequence 并追加到 `controlled_run_events`；事件回调只用于观察，回调错误不会改变 Run 结果。M8.2 的测试用合成 Python 脚本验证成功发布、非零退出、超时、取消、日志上限和事件顺序，不把这些脚本结果描述成农业模型指标。

M8.2 没有在本机宣称 Docker 资源隔离通过；Docker 只在 M8.1 验证了 argv 构造。M8.3 将失败 Run 转成 DebugCase，要求诊断假设有证据、修复在隔离分支/沙箱中执行并通过回归后才可记录解决。

## M8.3：DebugCase 与安全修复

失败 Run 先通过 `capture_failure()` 固化 observed error、Run 状态、日志/ staging 路径和非敏感环境事实；`classify_failure()` 与 `rank_hypotheses()` 只根据可观察关键词生成有 evidence reference 的候选假设。无足够证据时类别为 `unknown`，不会把“最可能”写成根因。

`DebugCaseRepository` 将诊断、修复提案、人工批准、回归失败/通过和 resolved 做成单向门禁。`SafeRepairWorkspace` 只在批准后复制失败 Run 的 workspace，拒绝 symlink、绝对路径、`..` 逃逸和哈希不匹配，并用 argv 在隔离目录执行 regression command。原始 staging 和主工作树不会被修改；只有回归通过后 DebugCase 才能进入 resolved。
