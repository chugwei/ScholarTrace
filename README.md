# 研迹 ScholarTrace

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**把研究问题、文献证据、实验记录和论文主张连成一条可审计链路。**

ScholarTrace 是一个本地优先的科研工作台，面向需要长期迭代、人工审批和来源追溯的研究项目。它用版本化领域对象保存“问题如何形成、证据来自哪里、实验如何执行、结论由什么支持”，并通过 CLI、FastAPI 和轻量 Web 工作台提供统一入口。

项目优先解决科研过程的可追溯性与可复现性，而不是自动生成未经验证的科研结论。LLM 输出、合成样例和离线演示只能作为候选或工程验证，不能替代真实数据、来源核验与研究者审批。

## 核心能力

- **研究问题与人工门禁**：基于 LangGraph + SQLite Checkpoint 保存项目状态，支持暂停、恢复、批准、拒绝、修改、版本冻结和回滚审计。
- **文献与证据链**：管理本地 PDF 和元数据，提供 SHA-256 去重、Crossref/OpenAlex 查询降级、项目级文献审核、Chunk 检索与可定位的 EvidenceCard。
- **研究设计与实验追踪**：版本化 Pipeline、数据采集协议、算法候选与 ExperimentPlan；保存 Run Manifest、数据/代码版本、独立重算指标和 Claim 证据状态。
- **受控运行与产物复现**：使用 argv 白名单、超时、取消、事件日志和失败隔离运行实验；图表可从已验证指标重建为 PNG、SVG 和 PDF。
- **论文契约与引用检查**：管理 Manuscript、Section Contract 和 Claim Ledger，执行离线 BibTeX 解析、引用缺失检查、数字一致性与来源回溯门禁。
- **本地服务与交付边界**：提供 FastAPI、SSE 时间线、Web 工作台、Manifest 绑定推理、交付清单校验、Compose staging、健康探针与受验证回滚。

## 快速开始

### 1. 安装

需要 Python 3.12+、[uv](https://docs.astral.sh/uv/) 和 Git。

```bash
git clone https://github.com/chugwei/ScholarTrace.git
cd ScholarTrace
uv sync --all-groups
```

### 2. 启动应用模式或 Web 工作台

**独立桌面应用**（推荐）：构建一次无控制台的独立可执行文件，之后双击即可使用，
用户数据保存在 `%LOCALAPPDATA%\ScholarTrace`：

```powershell
uv sync --all-groups
uv run pyinstaller scripts/app.spec --noconfirm   # 或 .\scripts\build-app.ps1
# 生成 dist\ScholarTrace.exe，双击运行
```

开发仓库内也可用应用模式命令（pywebview 桌面窗口，Windows 使用系统自带 WebView2
运行时；缺失或无桌面环境时可用 `--browser` 回退到默认浏览器）：

```bash
uv run scholartrace app
```

桌面窗口先显示加载页，服务就绪后自动进入工作台；关闭窗口即退出。Windows 下也可
双击仓库根目录的 `ScholarTrace.bat`。传统浏览器方式仍然可用：

```bash
uv run scholartrace web
```

打开 <http://127.0.0.1:8000>。默认业务数据库和 LangGraph checkpoint 保存在已忽略的 `.scholartrace/` 目录中。

### 3. 使用 CLI 创建可恢复项目

仓库提供一个农业视觉研究问题样例，可直接用于离线体验：

```bash
uv run scholartrace project create agriculture-demo \
  --question-file examples/agriculture-vision-project/research-question.json

uv run scholartrace project show agriculture-demo
uv run scholartrace project continue agriculture-demo
```

PowerShell 可将续行符 `\` 改为反引号，或把命令写在同一行。

### 4. 可选：LLM 研究问题候选

LLM 只用于生成待人工复核的结构化研究问题候选，响应必须通过领域校验，不会自动写入
数据库。服务端通过环境变量配置（密钥只在服务端读取，不进入源码或浏览器）：

```powershell
$env:SCHOLARTRACE_LLM_BASE_URL = "https://api.z.ai/api/anthropic"
$env:SCHOLARTRACE_LLM_API_KEY  = "<your-key>"
$env:SCHOLARTRACE_LLM_MODEL    = "glm-5.3"
uv run scholartrace app
```

完整变量见 [.env.example](.env.example)。`uv run scholartrace app` 不会自动加载
`.env` 文件；Docker Compose 会读取根目录中被 Git 忽略的 `.env`。出现在聊天或日志
里的密钥应先轮换再使用。

## 工作方式

```mermaid
flowchart LR
    Q["研究问题<br/>版本与审批"] --> L["文献目录<br/>审核与检索"]
    L --> E["EvidenceCard<br/>来源片段"]
    E --> D["研究设计<br/>算法候选"]
    D --> X["实验计划<br/>Run 与指标"]
    X --> F["图表与论文<br/>Claim 检查"]
    F --> P["API / Web<br/>交付与验证"]
```

每个阶段都保留版本、状态和来源关系；需要正式发布的研究对象必须经过人工门禁。SQLite 保存领域记录，LangGraph Checkpoint 保存流程状态，文件产物通过相对路径和 SHA-256 与记录绑定。

## 真实性边界

以下内容尚不能从仓库中的合成或离线样例推导出来：

- 真实农业视觉模型的效果与泛化能力；
- 真实文献语义召回质量或创新性结论；
- 真实数据采集、生产部署、现场验证与论文投稿结果；
- 任何未经来源核验和人工审批的 LLM 生成结论。

`examples/` 中的内容均为合成、脱敏或离线契约样例，不是科研证据。

## 项目结构

```text
src/scholartrace/   核心领域、流程、持久化、API 与 CLI
examples/           合成研究场景与交付契约样例
scripts/            应用构建与启动脚本
ScholarTrace.bat    Windows 双击启动入口
```

## 贡献

欢迎提交 Issue 和 Pull Request。请勿提交真实私有数据、论文全文、凭据、数据库、模型权重或大型运行产物。

## 许可证

本项目采用 [Apache License 2.0](LICENSE)。
