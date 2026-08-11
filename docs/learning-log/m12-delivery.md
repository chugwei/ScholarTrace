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
