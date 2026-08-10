# M8 v0.8.0 发布记录

日期：2026-08-11（Asia/Shanghai）

## 发布结果

- 功能分支 `feat/m8-runner-debugging` 已通过独立审查并以非 squash merge 合并到 `main`。
- merge commit：`99f72e19b2df87af4f9513672b33d5f93f743e63`。
- `main` 已推送，远端 `refs/heads/main` 与 `99f72e1` 一致。
- annotated Tag `v0.8.0` 已推送；Tag object：`265469d34df87d48f7039b3eb70be7b0cbf32deb`；peeled commit：`99f72e19b2df87af4f9513672b33d5f93f743e63`。

## 发布门禁

发布前后的 main smoke 均执行 `uv run python scripts/check.py`，结果为 Ruff 全部通过、`143 passed`、3 个合成 Fixture 校验通过。v0.8.0 wheel/sdist、独立 venv、CLI、0016 迁移、Apache-2.0、Git archive、内部文件排除、秘密/大文件扫描和 actionlint 均已验证；详见 [m8-release-candidate.md](m8-release-candidate.md)。

## 真实边界

M8 的 Runner、DebugCase 和 tracking 测试使用合成/脱敏 Run 与脚本，证明的是安全边界、状态和可追溯契约。Docker 未在本机实际执行训练，MLflow 未安装并实际返回 `unavailable`；没有真实农业视觉指标、真实文献证据、论文或部署结果。M9–M12 仍未完成。
