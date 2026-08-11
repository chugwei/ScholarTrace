# M11 `v0.11.0` 发布记录

日期：2026-08-11（Asia/Shanghai）

## 发布对象

- 合并提交：`88830470f269d2428cd5fc465b0d792848e3fcb7`（`release: ScholarTrace v0.11.0`）
- 候选分支：`feat/m11-web-workbench`
- 候选提交：`71d09ef029cbd20b2ca1410f728a0960fe753944`
- annotated Tag：`v0.11.0`
- GitHub Tag：[v0.11.0](https://github.com/chugwei/ScholarTrace/tree/v0.11.0)
- GitHub main：[commit 8883047](https://github.com/chugwei/ScholarTrace/commit/88830470f269d2428cd5fc465b0d792848e3fcb7)

## 发布前后验证

| 检查 | 结果 |
|---|---|
| 候选发布审查 | 通过，详见 `docs/verification/m11-release-candidate.md` |
| main smoke | 通过，`python -m scholartrace --help`、`python -m scholartrace web --help` exit 0 |
| main 全量门禁 | 通过，`scripts/check.py`；166 passed；3 个合成 Fixture |
| main 与远端 | 通过，`origin/main` 指向 `88830470f269d2428cd5fc465b0d792848e3fcb7` |
| Tag 与远端 | 通过，`refs/tags/v0.11.0` 为 annotated Tag，peeled commit 为 `8883047` |

## 能力边界

M11 发布证明 API、SSE 和 Web 工作台在本地/合成农业视觉黄金样例上的可复现垂直演示。它不证明真实文献全文、真实实验指标、真实设备、独立环境部署、监控回滚或现场科研结果；这些项目进入 M12，并且必须保留真实与合成证据的区分。
