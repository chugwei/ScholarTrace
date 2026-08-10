# ADR 0012：正式导出只接受已批准的成对设计

- 状态：已接受
- 日期：2026-08-11
- 范围：M5.4 PipelineSpec/DataCollectionProtocol Markdown/YAML 导出

## 背景

草案和已批准方案都需要可读预览，但把草案文件放进正式交付目录会让后续工具误以为采集协议已经发布。导出还必须保留版本和内容哈希，避免脱离数据库后无法追溯。

## 决策

`export_design_bundle()` 要求 PipelineSpec 与 DataCollectionProtocol 属于同一项目且状态均为 `approved`，否则不写文件。输出同时包含 Markdown、YAML、版本、父版本、批准者和 content SHA-256；比较报告也只描述结构变化，不添加科研结论。文件先写临时路径再替换，重复导出保持确定性。

## 取舍

- 正式导出不提供 draft 参数；研究者可以直接查看数据库或未来 UI 预览草案，避免正式目录污染。
- PyYAML 作为显式依赖保证独立环境可复现，YAML 只承载结构化契约，不承载大文件或真实数据。
- 导出通过不等于数据采集完成，真实授权和现场验证留在 M12。

## 验证

`tests/integration/test_m5_design_export.py` 覆盖 draft 阻断、approved 双方案输出、YAML 重读、中文 Markdown、版本/SHA-256 保留和重复导出字节一致。
