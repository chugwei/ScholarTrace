# M12.3 Docker Compose/Staging 验收

日期：2026-08-11（Asia/Shanghai）

## 验收命令与结果

```text
docker compose config
通过；服务、只读交付挂载、健康检查、非特权约束和 Manifest 参数解析成功

docker compose build --no-cache
通过；镜像 scholartrace-scholartrace 构建成功

docker compose up -d
通过；容器启动

docker compose ps
healthy；0.0.0.0:8000->8000/tcp

GET http://127.0.0.1:8000/health
{"status":"ok","version":"0.11.0"}

POST http://127.0.0.1:8000/api/inference
200；返回 delivery_id、manifest_sha256、fixture 预测和 synthetic_fixture 警告

docker compose logs --no-color --tail=40
通过；Uvicorn 启动、health 和 inference 请求均为 200

docker compose down -v
通过；容器、Staging 命名卷和网络已清理
```

静态契约测试 `tests/integration/test_m12_compose_contract.py` 通过 2 个用例，验证 Dockerfile 的非 root/healthcheck 和 Compose 的 read-only/capability/Manifest 配置。

## 边界

本批次使用 `examples/delivery/` 的合成/脱敏 Fixture；健康状态和推理响应只证明本地容器链路，不能证明生产可用性、真实模型效果、真实数据合规或现场部署。
