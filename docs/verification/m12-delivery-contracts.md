# M12.1 Delivery Manifest/Model Card/Data Card 验收

日期：2026-08-11（Asia/Shanghai）

## 范围

本批次建立交付清单、Model Card、Data Card、证据等级和文件 SHA-256 验证器。清单可写入 staging 目录，但尚未宣称推理服务、Docker Compose、独立部署或真实场景验证完成。

## 验收命令与结果

```text
uv run ruff format --check src tests scripts
通过，133 files already formatted

uv run ruff check src tests scripts
通过，All checks passed

uv run python scripts/check.py
Ruff format/check: passed
pytest: 169 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.

uv run pytest tests/unit/test_m12_delivery.py -q
3 passed
```

测试覆盖确定性 Manifest 哈希、原子写入、完整交付树、篡改检测、路径穿越、重复文件、`real_field` 验证记录和合成交付不得标为 `verified`。

## 证据边界

测试使用 `lychee-pest-detection` 合成/脱敏 Fixture；Model Card 的指标只表示 Fixture/离线契约可验证，Data Card 明确标记非田间样本。没有提交模型权重、私有数据或真实现场记录。
