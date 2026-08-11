# 本地 Staging Compose

根目录的 `docker-compose.yml` 启动一个只读交付挂载的 ScholarTrace API：

```bash
docker compose up --build -d
curl http://127.0.0.1:8000/health
docker compose ps
docker compose down -v
```

Compose 使用 `examples/delivery/` 的合成/脱敏 Manifest，SQLite 状态写入命名卷 `staging_state`。容器以非 root 用户运行，丢弃 Linux capabilities，交付目录只读；这只是本地 Staging smoke，不是生产部署或真实现场验证。
