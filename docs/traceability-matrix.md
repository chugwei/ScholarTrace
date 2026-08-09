# 需求追溯矩阵

状态含义：`implemented-tested`、`implemented-unverified`、`contract-only`、`planned`、`blocked`。

| 计划需求 | 实现 | 测试/证据 | 版本 | 状态 |
|---|---|---|---|---|
| M0 Python 3.12 + uv + src layout | `pyproject.toml`, `.python-version`, `src/scholartrace/` | `tests/unit/test_package.py`, `uv.lock` | v0.0.1 | implemented-tested |
| M0 范围与非目标 | `docs/product-scope.md` | 文档审查 | v0.0.1 | implemented-unverified |
| M0 科研真实性与数据安全 | `docs/research-integrity.md` | 文档审查、秘密扫描 | v0.0.1 | implemented-unverified |
| M0 风险登记 | `docs/risk-register.md` | 文档审查 | v0.0.1 | implemented-unverified |
| M0 ADR 机制 | `docs/adr/0001-progressive-evidence-first-architecture.md` | 文档审查 | v0.0.1 | implemented-unverified |
| M0 架构与学习日志 | `docs/architecture.md`, `docs/learning-log/m0-foundations.md` | `docs/verification/m0-review.md` | v0.0.1 | implemented-tested |
| M0 全新环境安装与构建 | `pyproject.toml`, `uv.lock` | `docs/verification/m0-acceptance.md` | v0.0.1 | implemented-tested |
| M0 3 个脱敏 Fixture | `tests/fixtures/projects/`, `src/scholartrace/fixtures.py`, `examples/agriculture-vision-project/` | `tests/unit/test_fixtures.py`, `tests/integration/test_fixture_catalog.py`, `scripts/validate_fixtures.py` | v0.0.1 | implemented-tested |
| M0 CI | `.github/workflows/quality.yml`, `scripts/check.py` | [quality Run #1](https://github.com/chugwei/ScholarTrace/actions/runs/31313652417) | v0.0.1 | implemented-tested |
| M0 LICENSE | `LICENSE`, `pyproject.toml`, `README.md` | `tests/unit/test_package.py`, wheel 内容检查 | v0.0.1 | implemented-tested |
| M1–M12 | `docs/roadmap.md` | 尚未实现 | v0.1.0–v1.0.0 | planned |
