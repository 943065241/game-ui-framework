# AIPG — AI 生产与治理框架

[English](README.md) | **简体中文**

> 构建受治理的 AI 生产系统，而不只是 Prompt。

AIPG 是通用 AI 生产运行时。GUIF 是它的视觉生产 Domain Pack 与兼容实现。

## 项目状态

- 开发版本：[`1.1.0-dev.10`](VERSION)
- 已发布包：`aipg-framework==1.1.0b1`
- 分支策略：直接提交到 `main`
- 最近验证基线：`1.1.0-dev.8` 已通过 Python 3.10、3.11、3.12 CI
- 当前重点：整理仓库并统一文档事实来源

权威项目文档：

- [当前实现状态](docs/PROJECT_STATUS.md)
- [路线图](ROADMAP.md)
- [架构](docs/AIPG_ARCHITECTURE.md)
- [Workflow Runtime](docs/AIPG_WORKFLOW_RUNTIME.md)
- [变更记录](CHANGELOG.md)
- [GUIF 迁移](docs/MIGRATING_GUIF_TO_AIPG.md)

## 当前架构

```text
AIPG
├─ runtime.py          Workflow 图、状态、调用栈与验证
├─ engine.py           生命周期与图执行
├─ recovery.py         Checkpoint 恢复与 Capability 执行
├─ checkpoints.py      与存储实现无关的 Checkpoint 边界
├─ events.py           Runtime 事件分发
├─ capabilities.py     Tool 发现与受治理执行
├─ artifacts.py        通用 Artifact 注册与血缘
├─ context.py          Project 与 Standalone 上下文
└─ domains/            Domain Pack 模型与注册

GUIF
└─ 视觉生产语义、工作流、检查、导出与兼容 API
```

## 当前能力

- 分层 Workflow 执行与嵌套 Subworkflow
- Sequence、Selector、确定性 Parallel、Condition、Action、Approval、Review
- Event Bus 与生命周期状态转换
- Checkpoint 持久化边界、恢复与可续跑节点游标
- 基于 Capability 的 Tool 发现与 Provider 执行
- Tool 健康、配置校验、超时、重试与 fallback 治理
- 通用 Artifact 血缘与 Domain Pack 注册

完整能力矩阵和明确限制统一维护在 [PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

## Tool 路由

```text
Workflow
→ CapabilityRequirement
→ ToolRegistry
→ ToolAdapter
→ Provider
```

`resolve()` 负责向后兼容的 Capability 发现；健康、配置、超时、重试和 fallback 在执行阶段应用。

## 开发

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

macOS 或 Linux 使用 `.venv/bin/python`。

## 兼容策略

AIPG 1.x 在通用职责迁移到 `aipg` 的过程中，继续保留现有 `guif` 包、命令、Skill、Schema 和记录。

## 文档规则

- `VERSION`：唯一开发版本
- README：简短公开入口
- `PROJECT_STATUS.md`：当前实现事实
- `ROADMAP.md`：只记录未来计划
- `CHANGELOG.md`：已完成历史
- 架构与 Runtime 文档：长期设计与行为

以后每次直接迭代 `main` 都必须同步更新 `VERSION`、README 状态，并在适用时更新 CHANGELOG。

## License

MIT。
