# AIPG — AI 生产与治理框架

[English](README.md) | **简体中文**

> 构建受治理的 AI 生产系统，而不只是 Prompt。

AIPG 是一个本地优先的 AI 生产工作流与治理框架。GUIF 继续作为游戏 UI 与视觉生产 Domain Pack。

## 当前迭代

- 开发版本：`1.1.0-dev.8`
- 最后更新：`2026-07-31`
- 分支策略：直接提交到 `main`
- 最新里程碑：Tool Runtime v2.1 兼容性修复

当前开发线已完成：

- AIPG 自主管理的 Domain Registry
- 可执行 Workflow 生命周期与 Event Bus
- Workflow Graph 自动遍历
- Subworkflow 有限调用栈执行
- CheckpointStore 持久化边界
- 确定性 Checkpoint 恢复与续跑
- Capability → ToolAdapter → Provider 执行
- Tool 健康状态与配置校验
- 标准 Tool 错误与执行结果
- 超时、重试与 Provider fallback 策略
- 保持向后兼容的纯 Capability 工具发现

下一阶段计划：

- 第一个真实 Provider Adapter
- Scheduler 与持久化执行队列
- Artifact 生命周期 Runtime 与依赖图
- 将 GUIF Workflow 迁移到 AIPG Runtime

今后每次直接迭代 `main` 都必须递增这里的开发版本，并同步更新本节。

## 发布状态

`1.1.0-beta.1` 已发布。当前未发布迭代直接重构现有 AIPG，不新增第二套 Core，也不会整体推翻 GUIF。

- Python 包：`aipg-framework==1.1.0b1`
- 框架导入与命令：`aipg`
- 兼容导入与命令：`guif`
- 视觉领域 Skill：`$game-ui-framework`
- 框架治理 Skill：`$aipg-framework`

重要文档：

- [版本迭代记录](CHANGELOG.md)
- [AIPG 架构](docs/AIPG_ARCHITECTURE.md)
- [当前 AIPG / GUIF 重构](docs/AIPG_CORE_GUIF_ITERATION.md)
- [详细用户蓝图](docs/AIPG_USER_BLUEPRINT.md)
- [GUIF 到 AIPG 迁移指南](docs/MIGRATING_GUIF_TO_AIPG.md)

## 当前架构

```text
AIPG
├─ runtime.py          工作流图、状态、调用栈、验证
├─ engine.py           生命周期与图执行
├─ recovery.py         Checkpoint 恢复与确定性续跑
├─ checkpoints.py      与存储无关的 Checkpoint 边界
├─ events.py           Runtime 事件分发
├─ context.py          Project 与 Standalone 生命周期
├─ artifacts.py        Artifact 身份、状态、祖先与血缘
├─ capabilities.py     受治理的 Capability 路由与 Tool 执行
└─ domains/
   └─ visual.py        GUIF Visual Production 注册
```

AIPG 不需要理解按钮、透明通道、Theme、Mask 或视觉层级；这些属于 GUIF。未来 Code、Document、Video、Audio 和游戏内容领域可以复用同一套运行时契约。

## 运行模型

```text
Workflow
→ Subworkflow
→ Stage / Control Node
→ Action
→ CapabilityRequirement
→ ToolRegistry
→ ToolAdapter
→ Provider
```

## Tool Runtime 治理

`resolve()` 保持为兼容旧代码的 Capability 与 Feature 发现接口。健康状态、配置、重试、超时和 fallback 治理在真正执行 Tool 时应用。明确只需要可执行 Adapter 的调用方可使用 `available_only=True`。

执行策略支持：

- 超时边界
- 可重试错误的有限重试
- Provider 确定性 fallback
- 禁用 fallback
- 标准执行结果元数据
- 明确的不可用、配置、认证和超时错误

没有配置凭据、权限、费用、数据流与健康检查之前，AIPG 不声明 Tool 可用。

## 上下文模式

- `project`：长期上下文。GUIF 通常绑定 Theme、母版、已批准资产和导出目标。
- `standalone`：一次性任务，例如局部重绘、图片编辑、图片分层或效果图生产。

Figma 是 Tool 与结构化设计环境，不是第三种生命周期模式。

## 开发

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

macOS 或 Linux 使用 `.venv/bin/python`。

## 隐私与真实性

真实 Theme、Prompt、源图、会话记录、凭据、私有路径和生成产物默认保存在 Framework Git 与 Project Git 之外。公共测试和示例只使用虚构内容。

AIPG 不伪造图片像素、Tool 可用性、语义检查、候选结果或导出成功。

## 兼容策略

AIPG 1.x 保留现有 `guif` 包、命令、Skill、Schema、Theme、Source、Artifact 和 Candidate Change 契约。新的框架级集成使用 AIPG 命名，视觉领域集成可以继续使用 GUIF。

## License

MIT。
