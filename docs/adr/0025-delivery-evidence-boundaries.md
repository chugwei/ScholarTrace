# ADR 0025：交付清单必须绑定卡片、文件哈希和证据等级

- 状态：accepted
- 日期：2026-08-11
- 范围：M12.1 Delivery Manifest、Model Card、Data Card

## 决策

M12 的交付包以 `DeliveryManifest` 为索引，清单中的每个文件必须声明相对路径、大小和 SHA-256；Manifest 同时绑定 `ModelCard`、`DataCard`、源代码 revision、入口命令和证据等级。`synthetic_fixture`、`offline_test`、`staging` 与 `real_field` 是互斥的证据分类，`real_field` 必须引用独立的现场验证记录；合成数据不能把交付状态提升为 `verified`。

清单写入采用确定性 JSON（排序键、固定 UTF-8 和换行）并使用原子替换；验证器只读交付根目录，拒绝路径穿越、缺失文件、大小不符和哈希不符。卡片是交付声明，不是模型或数据质量的自动证明。

## 理由

部署最容易丢失的不是代码，而是“这个文件来自哪一版、这个指标属于哪类证据、交付包是否被改过”。把 provenance 放在同一清单中，独立环境可以在启动前复核文件和证据边界；显式分类则防止把 Fixture 或离线 smoke 当成真实田间结果。

## 后续影响

M12.2 的推理接口和 Docker Compose 必须消费 Manifest，而不是扫描任意目录。真实场景验证、监控和回滚仍需额外记录，不得由 Manifest 单独推断。
