# 真实场景验证记录模板

本目录用于存放真实场景（`real_field`）验证记录。每条记录必须与 `FieldValidationRecord` 契约对齐，字段要求见 `src/scholartrace/schemas/delivery.py` 和 ADR 0029。

## 使用约束

- 只有 `real_field` 记录支持“已用于真实场景”的表述。合成 Fixture、离线测试和 Staging 结果必须分别标记为 `synthetic_fixture`、`offline_test` 和 `staging`，且不得携带本模板中的现场环境字段。
- 所有真实数据、真实设备、真实操作人员、伦理批准和隐私审查必须由用户提供；不得由仓库自动生成或推断。
- 记录必须绑定产生它的代码版本、数据版本、模型版本和交付 Manifest 哈希。

## 记录模板

复制以下结构，填写真实字段，保存为 `docs/field-validation/<site>-<date>.md`。

```text
record_id: <唯一记录 ID，例如 orchard-a-2026-08>
evidence_class: real_field
source_ref: <真实数据来源引用>
validation_record_ref: <本文件或外部验证报告引用>

conducted_at: <现场执行时间，ISO 8601，含时区>
summary: <一句话现场验证摘要>

environment:
  site_name: <现场名称>
  location_description: <地点描述，精确到场景需要且不暴露隐私的粒度>
  device_description: <采集设备描述>
  capture_conditions: <光照、天气、时段等采集条件>
  operator_name: <操作人员，可在私有记录中具名>
  privacy_review: <隐私审查结论，例如脱敏处理>
  ethics_approval_ref: <伦理批准编号，必填>

provenance:
  code_version: <代码版本，例如 git commit>
  data_version: <数据版本>
  model_version: <模型版本>
  manifest_delivery_id: <交付 Manifest delivery_id>
  manifest_sha256: <交付 Manifest SHA-256>

rollback_outcome:
  attempted: <true|false>
  active_release_id: <若 attempted 为 true，填回滚后的 active release id>
  notes: <备注，例如未触发回滚的原因>

results:
  - <真实指标项，必须可追溯到现场原始数据，不得从合成结果推断>
```

## 提交前检查

在把任何 `real_field` 记录纳入发布前，确认：

1. 现场数据、设备、操作人员、伦理批准和隐私审查均为用户提供，不是合成或推断。
2. 代码、数据和模型版本与产生该结果的运行一致。
3. `FieldValidationRecord` 可以从上述字段无异常构造（运行 Schema 校验）。
4. `FieldValidationSummary` 若声明 `real_field` 结论，只包含 `real_field` 记录。

未满足以上条件的记录必须降级为 `synthetic_fixture`、`offline_test` 或 `staging`，并在 summary 中明确说明不是真实场景结果。
