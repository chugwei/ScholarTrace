# ScholarTrace 离线交付样例

这是 M12 的合成/脱敏交付包样例，仅用于验证 Manifest、离线推理和 Docker Compose 的连接性。

- `model-card.md` 和 `data-card.md` 说明当前 Fixture 的用途与限制；
- `sample-inputs/lychee-fixture.json` 不是田间图像，也不产生真实农业结论；
- `delivery-manifest.json` 登记所有文件的 SHA-256 和证据等级；
- `scholartrace infer` 或 Compose API 的响应必须保留 `synthetic_fixture` 警告。
