# M9 `v0.9.0` 发布记录

日期：2026-08-11（Asia/Shanghai）

## 发布事实

- 目标仓库：[https://github.com/chugwei/ScholarTrace](https://github.com/chugwei/ScholarTrace)
- 合并提交：`4e60f4880d5db71d25d4ffa00dae7da8e8569206`（`release: ScholarTrace v0.9.0`）
- annotated Tag：`v0.9.0`
- Tag object：`0290f40de7f769e47d1ea86d69c03a5362eb1750`
- Tag peeled commit：`4e60f4880d5db71d25d4ffa00dae7da8e8569206`
- GitHub 分支：[main](https://github.com/chugwei/ScholarTrace/tree/main)
- GitHub Tag：[v0.9.0](https://github.com/chugwei/ScholarTrace/tree/v0.9.0)

## 发布前后验证

合并前的 `feat/m9-figures` 候选通过了 Ruff、149 个测试、3 个 Fixture、独立 wheel/venv、0017 迁移升降级、Apache-2.0、公开包内部文件排除、秘密/大文件扫描、Docker actionlint 和 PNG/SVG/PDF 视觉检查。合并后在 `main` 再次运行：

```text
uv run python scripts/check.py
Ruff format/check: passed
pytest: 149 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.
```

远端 Ref 已核验：`origin/main` 指向 `4e60f4880d5db71d25d4ffa00dae7da8e8569206`，`refs/tags/v0.9.0` 指向 Tag object `0290f40de7f769e47d1ea86d69c03a5362eb1750`，peeled ref 指向同一 merge commit。

## 能力边界

M9 证明的是 FigureSpec 到 PNG/SVG/PDF 的确定性 Bundle、数据与脚本 provenance、MetricResult 数值一致性和当前合成/脱敏输入下的视觉可读性。它不证明真实农业视觉训练、真实文献结论、论文、Web、部署或现场验证；这些仍由 M10–M12 和真实场景验收负责。
