# 风险登记

| ID | 风险 | 影响 | 缓解措施 | M0 状态 |
|---|---|---|---|---|
| R-001 | 范围过大 | 长期无法形成可验收版本 | 严格 M0→M12 门禁，M6 才形成首个展示切片 | active |
| R-002 | 过早引入多 Agent | 调试与评测复杂 | 前六个里程碑使用单图和模块化节点 | controlled |
| R-003 | 文献或引用伪造 | 科研可信性破坏 | DOI/URL/原文片段/BibTeX 强校验 | planned |
| R-004 | 噪声文献污染证据 | RAG 输出不可靠 | candidate/approved/rejected 与 EvidenceCard | planned |
| R-005 | LLM 编造实验结果 | 学术不端 | Results 只读已验证 MetricResult | planned |
| R-006 | 数据泄漏 | 指标虚高 | 采集协议、划分检查和数据版本追踪 | planned |
| R-007 | 实验不可复现 | 结论不可验证 | Git SHA、环境、配置、种子和 Run Manifest | planned |
| R-008 | 自动执行破坏数据 | 数据或产物丢失 | Sandbox、只读输入、原子发布、人工审批 | planned |
| R-009 | 图表误导 | 错误科研结论 | 数据/脚本/图绑定与数值、视觉双检查 | planned |
| R-010 | 夸大真实部署 | 交付与简历失真 | 分开记录离线、合成、实验室和现场验证 | active |
| R-011 | 未确定许可证 | 无法明确复用和发布边界 | M0 Tag 前确认许可证类型 | blocked |
