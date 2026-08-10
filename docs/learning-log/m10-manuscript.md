# M10 学习日志：论文契约与证据绑定

M10 将 M4 的 EvidenceCard、M7 的 MetricResult、M9 的 FigureSpec 接到论文对象，但先建立可审计契约，再允许生成章节文本。M10.1 的真实代码在 `src/scholartrace/schemas/manuscript.py`、`src/scholartrace/persistence/manuscript_repository.py` 和迁移 `0018`。

## 新概念与真实问题

- **Manuscript** 是项目级、可版本化的论文容器。父版本和 `content_sha256` 防止在同一项目中静默覆盖历史。
- **SectionContract** 把章节目的、必须引用的 Claim/EvidenceCard/MetricResult/FigureSpec 写成输入契约。Conclusion 默认不允许引入新 Claim。
- **Claim Ledger** 是重要事实陈述的清单。`supported` 不是写作语气，而是经过 Repository 检查后的状态；没有来源的陈述只能保持 `planned` 或 `insufficient`。

数据流为：

```text
EvidenceCard / validated Run / verified MetricResult
                ↓ explicit IDs
          Claim Ledger (planned → supported/insufficient)
                ↓ required IDs
          SectionContract (section-level obligations)
                ↓ parent/version/hash
          Manuscript draft
```

当前测试使用脱敏农业视觉项目和合成指标。它证明项目隔离、版本链、迁移回滚和来源状态门禁，不是真实论文或真实农业结果。

## LangGraph 概念在本批次中的位置

M10.1 先把事实存储契约固定下来，尚未新增 Manuscript Graph。后续图可以把这些概念映射为：State 保存当前 manuscript/section ID，Node 负责收集来源或生成候选段落，Edge 根据 SectionContract 的缺口路由，Reducer 只合并诊断而不改写指标，Checkpointer 保存人工修订暂停点，interrupt/resume 等待人工确认，Command(resume=...) 提交修订决定，Subgraph 隔离章节写作，Tool 执行 BibTeX 解析和数字检查。Repository 是确定性 Tool 的持久化边界，不能被 LLM 绕过。

## 常见错误与测试

- 把训练日志或未验证指标写成 supported result Claim：测试要求 verified/final MetricResult。
- 把另一个项目的 evidence/run/metric ID 写入 Claim：Repository 逐类检查 project_id。
- 直接复用 Manuscript ID 保存新版本：测试要求单调版本和 parent_manuscript_id。
- 让 Conclusion 合同允许新 Claim：Schema 在构造时拒绝。

M10.2 将在不改变这些边界的前提下实现 BibTeX、引用解析和章节草稿；M10.3 再实现一致性报告。
