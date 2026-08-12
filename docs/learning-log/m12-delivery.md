# M12 学习日志：交付清单、卡片与证据边界

M12 的第一个批次把“能运行的代码”转成“能交付、能复核的包”。`DeliveryManifest` 是索引，不是新的科研状态机：它引用 `ModelCard`、`DataCard`、源 revision 和每个交付文件的 SHA-256；`verify_delivery_tree()` 只读文件并报告缺失、大小不符或哈希不符。

## 新概念与真实问题

- Model Card 说明模型的任务、用途、越界用途、训练/评估数据和限制，避免部署文档只写一个模型名字。
- Data Card 说明数据来源、采集协议、预处理、切分、隐私审查和局限性，避免把测试 Fixture 误写成田间数据。
- Delivery Manifest 把卡片、入口命令、源代码 revision 和文件哈希放到一个可验证的交付索引中。
- EvidenceClass 明确区分 `synthetic_fixture`、`offline_test`、`staging` 和 `real_field`；现场证据必须有独立验证记录引用。

## 数据如何流动

农业视觉交付示例从 `tests/fixtures/projects/lychee-pest-detection.json` 读取脱敏项目说明，生成 Model/Data Card，再把 README、卡片和推理入口写入交付根目录。`DeliveryArtifact` 记录文件相对路径、大小和 SHA-256；独立环境运行验证器后才知道包是否完整。当前批次没有模型权重，也不伪造真实指标或现场记录。

## 最小运行示例

```python
from scholartrace.delivery import verify_delivery_tree

report = verify_delivery_tree(delivery_root, manifest)
assert report.passed
```

`write_delivery_manifest()` 使用排序键和原子替换，因此同一 Manifest 的内容哈希稳定，半写入文件不会成为正式产物。

## 常见错误与后续关系

常见错误是使用绝对路径、重复文件、把 `real_field` 留空验证记录，或修改文件后忘记更新哈希。Pydantic 契约和 3 个单元测试覆盖这些边界；M12.2 将让推理接口读取已验证的 Manifest，之后再加入 Compose、Staging、监控/回滚和真实场景证据。当前结果仅是合成/离线交付契约，不是 v1.0.0。

## M12.2：Manifest 绑定推理

推理层把“输入、模型版本、交付包”连成一个可验证请求。`InferenceService` 先运行 `verify_delivery_tree()`，再检查输入路径在 Manifest 中、请求 SHA-256 与文件一致、Provider 版本与 Model Card 一致，最后才调用 `Predictor`。这相当于把 M8 的 Runner 安全边界延伸到交付边界：Provider 可以替换，provenance 校验不能替换。

离线示例使用 `FixturePredictor`，标签由输入内容哈希生成并带 `synthetic_fixture` 警告；它证明 API/CLI 的数据流和失败路径，不代表病虫害识别模型。未配置交付根目录的 API 返回 503，篡改文件返回 422，避免把缺失部署配置伪装成“推理成功”。

## M12.3：Compose Staging

Dockerfile 把当前 Python 包安装到 `python:3.12-slim`，以非 root 用户启动 `scholartrace web`；Compose 把交付包只读挂载，把 SQLite 状态放进命名卷，并用 `/health` 作为容器健康信号。健康检查只回答服务是否能响应，不代表模型或科研结果正确；推理响应仍必须带 Manifest 哈希和证据警告。

本地验收真实执行了镜像构建、容器启动、健康检查、离线推理和清理。由于输入是合成 Fixture，Staging 结果只能归入离线/合成证据，M12.4 仍要补监控与回滚，M12.5 需要真实场景输入和用户操作。

## M12.4：监控、回滚与交付包重建

这一批次把“服务能响应”和“当前版本可安全切换”拆成两个可验证问题。`HealthProbeResult` 是监控事件的结构化记录；它保存 endpoint、状态码、JSON 载荷、失败原因和检查时间，格式错误或网络失败不会被吞成成功。`ReleaseStore` 维护 active、previous 和 history，激活前重新验证 Delivery Manifest，失败时保持原 active release；回滚则交换已验证指针并留下历史。

数据流是：Staging `/health` → `probe_health()` → 结构化探针结果；交付目录 → `verify_delivery_tree()` → `ReleaseStore.activate()` → 原子 release state。`write_sha256sums()` 从 Manifest 中按相对路径排序生成校验和，排除自身后原子替换，因而重建后可以再次通过同一验证器。

最小示例：

```python
from scholartrace.delivery import ReleaseStore, probe_health, write_sha256sums

health = probe_health("http://127.0.0.1:8000/health")
assert health.ok
checksum = write_sha256sums(delivery_root, manifest)
state = ReleaseStore(state_path).activate(
    "release-2026-08-11", manifest, delivery_root, root_relpath="releases/current"
)
```

常见错误是只检查 HTTP 200、先写 active 再验证文件，或手工维护顺序不稳定的 `SHA256SUMS.txt`。单元测试覆盖这些失败路径；M12.5 将把证据等级从合成/离线扩展到用户提供的真实现场记录，M12.6 再在独立环境复跑整套交付与回滚。

## M12.5：真实场景验证记录与证据分层

这一批次解决的核心问题是：如何保证合成、离线和 Staging 结果永远不会被包装成“已用于真实场景”。答案是类型层的强绑定，而不是文档约定。

`FieldValidationRecord` 用 `model_validator` 把 `evidence_class` 和可携带字段直接绑定：`real_field` 记录必须同时带 `FieldEnvironmentContext`（现场地点、设备、采集条件、操作人员、隐私审查、伦理批准编号）和 `FieldProvenance`（代码/数据/模型版本 + Manifest 哈希）；而 `synthetic_fixture`、`offline_test` 和 `staging` 记录禁止携带现场环境上下文。这意味着无法在代码里“顺手”给一条合成记录加上 `site_name` 来模糊边界。

`FieldEnvironmentContext` 把 `operator_name` 和 `ethics_approval_ref` 设为必填，对应权威计划对真实场景验证的硬性要求：无操作人员、无伦理批准的现场主张不可验证。`FieldValidationSummary` 再加一层保护——`conclusion_class` 为 `real_field` 时只接受全由 `real_field` 记录组成的非空集合，`record_count_by_class` 报告全部四类计数，避免“缺失即零”的歧义。

数据流是：现场原始数据（用户提供）→ `FieldValidationRecord` → `FieldValidationSummary` → 发布说明/Model Card。当前仓库没有真实场景输入，所以本批次交付的是记录契约、分层门禁和填写模板，不是 `real_field` 证据。

常见错误是给合成记录填现场字段、把 Staging smoke 冒充田间结论，或用空记录集声明 `real_field`。6 个单元测试覆盖这些失败路径；在用户提供真实数据、设备、伦理确认和现场操作前，Goal 保持进行中。

## API 加固与公开项目呈现

批量并发评估暴露了两个边界问题：非法标识符穿过请求 Schema 后在 Repository 抛出 `ValueError`，并发研究问题写入则会争用同一个递增版本号。前者应在 HTTP 边界返回 422；后者没有数据损坏，但调用方需要收到可重试的 409，而不是内部 500。解决方式是复用唯一的标识符正则，并把数据库唯一约束冲突转换为明确的领域异常。

公开 README 也需要和内部实施记录承担不同职责。首页应先回答项目解决什么问题、如何启动、有哪些已实现能力和证据边界；详细里程碑、验收表和恢复信息继续留在状态文件与验证记录。通用缓存、IDE、日志、私有数据、模型和运行产物写入 `.gitignore`，而仅属于当前协作环境的计划、Prompt 与恢复记录保留在 `.git/info/exclude`，避免把个人工作流强加给所有贡献者。

README 的 CLI create/show/continue 与本地 Web `/health`、首页均已实际 smoke；统一质量门禁为 187 passed。这里验证的是公开入口和工程契约，不增加真实科研证据，也不改变 M12.5 的现场输入缺口。
