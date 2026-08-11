# ScholarTrace CLI

## 创建项目

```bash
uv run scholartrace project create PROJECT_ID \
  --question-file question.json \
  --thread-id THREAD_ID \
  --current-goal "定义可检验的研究问题"
```

`--thread-id` 默认等于 `PROJECT_ID`。`question.json` 必须是 UTF-8 编码，并包含 `problem`、`target_population_or_domain`、`inputs`、`expected_outputs`、`constraints`、`success_criteria`、`assumptions` 和 `unresolved_questions`。未知字段、空白必填文本和空核心列表会被拒绝。

## 继续项目

```bash
uv run scholartrace project continue PROJECT_ID
```

命令从业务数据库取得项目绑定的 thread，再从 SQLite Checkpointer 继续执行。M1 图没有人工中断点；当图已到 `END` 时，命令返回已保存的最终 State 摘要且不新增研究问题版本。

## 查看项目

```bash
uv run scholartrace project show PROJECT_ID
```

命令输出项目身份、当前阶段和所有研究问题版本。重要内容包含内容 SHA-256，便于验证幂等保存。

## 启动本地 Web 工作台

```bash
uv run scholartrace web \
  --host 127.0.0.1 \
  --port 8000 \
  --database .scholartrace/domain.db
```

打开 `http://127.0.0.1:8000/`；已有项目可使用 `?project=PROJECT_ID` 恢复工作区。工作台的 Run 时间线从持久事件快照开始，并通过 `live=true` SSE 接收增量事件。页面中的论文草稿必须经过人工审阅入口，合成/脱敏数据不会被标记为真实科研证据。

## 数据路径

默认路径：

- 业务数据库：`.scholartrace/scholartrace.db`
- Checkpoint：`.scholartrace/checkpoints.db`

可分别用 `--database` 和 `--checkpoints` 覆盖。`.scholartrace/`、`*.db`、`*.sqlite` 和 `*.sqlite3` 均被 Git 忽略。

## 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 命令成功，stdout 是 JSON 或帮助文本 |
| 1 | 项目/Checkpoint 不存在或身份冲突 |
| 2 | 参数、文件编码、JSON 或 ResearchQuestion Schema 无效 |
