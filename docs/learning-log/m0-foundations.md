# M0 学习日志：范围、契约和可复现骨架

## 新概念

M0 的核心概念不是“搭目录”，而是建立可验证的项目契约：范围契约约束现在能做什么，数据契约约束输入是什么，质量门禁约束什么证据才算通过，Git 历史记录每次可复现变化。

## 在 ScholarTrace 中解决的问题

科研软件容易出现界面先行、证据链滞后的问题。M0 把“尚未实现”写成明确边界，并用合成农业视觉 Fixture 验证安装和 Schema，而不是用演示内容代替文献、实验或部署证据。这让后续版本可以在稳定、可审查的基线上演进。

## 核心数据如何流动

`tests/fixtures/projects/*.json` 先由 `json` 模块解析，再进入 `ProjectFixture`。Pydantic 拒绝未知字段、错误枚举、私有数据标志、真实验证标志和本机绝对路径。目录校验器再检查数量与 `project_id` 唯一性。最终输出只有已验证 Fixture ID，不产生科研结论。

## 为什么选择当前方案

- 使用 src layout，防止测试意外导入仓库根目录中的未安装代码；
- 使用 uv 锁定开发依赖，让本地和 CI 使用同一依赖解析结果；
- 使用 Pydantic v2 的 `extra="forbid"` 和 Literal，尽早暴露契约漂移；
- 使用一个跨平台 Python 门禁脚本，避免 Windows 与 Linux CI 命令分叉；
- 不创建 M1–M12 空目录，只有实现和测试一起出现时才扩展架构。

## 最小运行示例

```python
from pathlib import Path

from scholartrace.fixtures import load_project_fixture

fixture = load_project_fixture(Path("tests/fixtures/projects/lychee-pest-detection.json"))
assert fixture.real_world_validation is False
```

完整门禁运行 `uv run python scripts/check.py`。

## 常见错误与测试

- 把 Fixture 称为真实项目：Literal 强制 `fixture_only_not_research_evidence` 和 `real_world_validation=false`；
- 提交本机数据路径：模型校验器拒绝 Windows、WSL、Linux/macOS 用户目录形式；
- 重复项目 ID：目录级负路径测试必须报错；
- Fixture 数量不足：少于三个时校验失败；
- Windows 全局临时目录权限异常：pytest 使用仓库内、被忽略的 `.pytest-tmp/`，保证测试仍可复现；
- 格式化范围过宽：Ruff 只检查 `src`、`tests` 和 `scripts`，避免把项目说明中的示例代码当作源码改写。

## 与前后里程碑的关系

M0 没有上一里程碑。它为 M1 提供安装、测试、CI、状态恢复规则和农业视觉输入契约。M1 会首次实现 LangGraph 的 State、Node、Edge、Reducer 与 Checkpointer；M0 文档中出现这些术语只表示路线，不表示它们已经可用。
