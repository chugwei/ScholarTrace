# ADR 0027：Compose Staging 只读挂载交付包，状态写入独立卷

- 状态：accepted
- 日期：2026-08-11
- 范围：M12.3 Docker Compose、Staging 和健康检查

## 决策

根目录 `docker-compose.yml` 只启动一个 API 服务：交付目录以只读 bind mount 挂载，SQLite 状态写入独立命名卷；容器使用非 root 用户、`no-new-privileges`、丢弃全部 capabilities、只读根文件系统和 `/tmp` tmpfs。健康检查只调用 `/health`，推理请求仍由 Manifest/Provider 门禁处理。

Compose 使用 `examples/delivery/` 合成样例，`docker compose up --build -d` 的成功只表示容器和离线接口可启动，不代表 Staging 已接入真实模型或真实数据。`docker compose down -v` 是本地验收后的清理步骤，不是生产回滚。

## 理由

交付包应该像输入证据一样不可被服务进程覆盖；状态和日志需要独立于镜像生命周期保存。最小权限和健康检查给后续 Staging/监控提供确定边界，同时不把本地 Docker smoke 误写成真实部署结果。

## 后续影响

M12.4 必须记录健康检查、日志、回滚和重建结果；生产环境还需要用户提供域名、凭据、资源限制和现场操作，不能由该 Compose 文件自动推断。
