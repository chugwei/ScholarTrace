# M12.2 Manifest 绑定推理接口验收

日期：2026-08-11（Asia/Shanghai）

## 范围

本批次增加 `InferenceRequest`/`InferenceResponse`、可替换 Provider、确定性的 `FixturePredictor`、`InferenceService`、`scholartrace infer` CLI 和可选 `POST /api/inference`。服务只读取 Manifest 登记的输入，并在哈希/版本/交付树验证失败时拒绝调用 Provider。

## 验收命令与结果

```text
uv run pytest tests/unit/test_m12_delivery.py tests/unit/test_m12_inference.py -q
6 passed

uv run ruff format --check src tests scripts
通过，137 files already formatted

uv run ruff check src tests scripts
通过，All checks passed

uv run python scripts/check.py
Ruff format/check: passed
pytest: 172 passed
Fixture validation: 3 synthetic project fixtures passed
ScholarTrace quality gate passed.
```

目标测试覆盖合成输入预测、非田间证据警告、交付文件篡改、配置 API、未配置 API 的 503 降级和 Manifest 绑定。

## 边界

Fixture Provider 的标签由输入 SHA-256 确定性生成，只用于离线接口连通性；没有真实模型权重、真实图像、真实指标或现场结果。M12.3 才加入 Docker Compose/Staging，真实 Provider 和真实场景仍需要用户提供资源与验证记录。
