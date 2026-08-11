# M12.4 监控、回滚与交付包重建验收

日期：2026-08-11（Asia/Shanghai）

## 范围

本批次为本地 Staging 增加无第三方依赖的健康探针、原子 release pointer、失败激活保护、上一版本回滚和 `SHA256SUMS.txt` 重建。它解决的是交付状态管理问题，不把本地健康响应解释为模型质量或真实现场结果。

## 设计与验证

- `probe_health()` 将 HTTP 状态、JSON 载荷、网络错误和非对象响应统一为 `HealthProbeResult`，便于监控层记录失败原因。
- `ReleaseStore.activate()` 先完整验证 Delivery Manifest，再原子写入 active/previous 指针；失败交付不会覆盖当前 active release。
- `ReleaseStore.rollback()` 只在存在 previous release 时交换指针，并追加历史记录；没有可回滚版本时明确失败。
- `write_sha256sums()` 按相对路径排序、排除自身并原子替换清单文件，重建结果可再次通过交付树验证。

## 验收命令与结果

```text
uv run pytest tests/unit/test_m12_release.py -q
3 passed

uv run pytest tests/unit/test_m12_delivery.py tests/unit/test_m12_inference.py tests/unit/test_m12_release.py tests/integration/test_m12_compose_contract.py -q
11 passed

uv run python -c "... verify_delivery_tree(examples/delivery, delivery-manifest.json) ..."
passed=true；SHA256SUMS.txt 的 SHA-256 为 fe71be847bd241d213078f5c1fd985c24abfe32cbce651d9f672aabb9114f8ec
```

测试覆盖成功探针、HTTP/网络/格式失败、双版本激活、无损回滚、篡改后拒绝激活、原子状态文件和清单重建。

## 证据边界

当前交付根目录仍是 `synthetic_fixture`。健康探针与回滚测试证明状态转换和失败保护可复现，不证明真实模型、真实数据、生产监控或田间部署。M12.5 需要用户提供真实数据、设备、伦理确认和现场操作记录。
