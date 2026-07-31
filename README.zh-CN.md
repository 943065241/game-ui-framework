# AIPG — AI 生产与治理框架

[English](README.md) | **简体中文**

> 构建受治理的 AI 生产系统，而不只是 Prompt。

AIPG 是一个本地优先的 AI 生产工作流与治理框架，负责路由、执行、检查、修订和导出 AI 生产任务。GUIF 继续作为游戏 UI 与视觉生产 Domain Pack。

ChatGPT / Codex 是默认 Host。图片生成、语义视觉、结构化布局、游戏引擎以及未来的生产能力都是可替换的 Tool 契约，而不是硬编码依赖。

## 当前迭代

- 开发版本：`1.1.0-dev.6`
- 最后更新：`2026-07-31`
- 分支策略：直接提交到 `main`
- 最新里程碑：可恢复的 Workflow Runtime 与 Capability 执行链路

当前开发线已完成：

- AIPG 自主管理的 Domain Registry
- 可执行 Workflow 生命周期与 Event Bus
- Workflow Graph 自动遍历
- Subworkflow 有限调用栈执行
- CheckpointStore 持久化边界
- 确定性 Checkpoint 恢复与续跑
- Capability → ToolAdapter → Provider 执行

下一阶段计划：

- Scheduler 与持久化执行队列
- Artifact 生命周期 Runtime 与依赖图
- 将 GUIF Workflow 迁移到 AIPG Runtime

今后每次直接迭代 `main` 都必须递增这里的开发版本，并同步更新本节，打开仓库首页即可判断是否有新迭代。

## 发布与迭代状态

`1.1.0-beta.1` 已发布。当前未发布迭代直接重构现有 AIPG，不再旁路新增第二套 Core，也不会整体推翻 GUIF。

- Python 包：`aipg-framework==1.1.0b1`
- 框架导入与命令：`aipg`
- 兼容导入与命令：`guif`
- 视觉领域 Skill：`$game-ui-framework`
- 框架治理 Skill：`$aipg-framework`
- Workflow Schema v1、v2、v3 保持可读取

重要文档：

- [版本迭代记录](CHANGELOG.md)
- [AIPG 架构](docs/AIPG_ARCHITECTURE.md)
- [当前 AIPG / GUIF 重构](docs/AIPG_CORE_GUIF_ITERATION.md)
- [详细用户蓝图](docs/AIPG_USER_BLUEPRINT.md)
- [GUIF 到 AIPG 迁移指南](docs/MIGRATING_GUIF_TO_AIPG.md)
- [母版引导式分层创作](docs/MASTER_GUIDED_LAYER_WORKFLOW.md)
- [发布说明](docs/RELEASE_NOTES_AIPG_1_1_BETA1.md)
- [GUIF 产品规格](docs/GUIF_PRODUCT_SPEC.md)

## 当前架构

```text
AIPG
├─ runtime.py          工作流图、状态、调用栈、验证
├─ engine.py           生命周期与图执行
├─ recovery.py         Checkpoint 恢复与确定性续跑
├─ checkpoints.py      与存储实现无关的 Checkpoint 边界
├─ events.py           Runtime 事件分发
├─ context.py          Project 与 Standalone 生命周期
├─ artifacts.py        Artifact 身份、状态、祖先与血缘
├─ capabilities.py     Capability 路由与 Tool Adapter 执行
└─ domains/
   └─ visual.py        GUIF Visual Production 注册

GUIF 兼容实现层
├─ 既有工作流与 CLI
├─ Theme 与视觉上下文
├─ 视觉 Artifact 语义
├─ 视觉 Review 与 Exporter
└─ 外部视觉 Tool Adapter
```

这次重构采用渐进迁移：把既有 GUIF 中领域无关的职责逐步提升到 AIPG，同时保留现有 `guif` API、命令、Schema、记录和生产流程。确认回归通过后，才删除 GUIF 内部的重复基础设施。

AIPG 不需要理解按钮、透明通道、Theme、Mask 或视觉层级；这些属于 GUIF。未来 Code、Document、Video、Audio 和游戏内容领域可以复用同一套运行时契约。

## 运行模型

Workflow Definition 使用类似行为树的图结构，运行时使用分层状态机和有限 Workflow Stack。

```text
Workflow
→ Subworkflow
→ Stage / Control Node
→ Action
→ Tool Invocation
```

父工作流调用子工作流后进入等待状态；子工作流完成并返回声明的结果后，父工作流继续执行。Workflow 状态与 Artifact 状态独立管理。

## 上下文模式

- `project`：长期上下文。GUIF 通常绑定 Theme、母版、已批准资产、规则与导出目标。
- `standalone`：一次性任务，例如局部重绘、图片编辑、图片分层或单张效果图生产。

Figma 是 Tool 与结构化设计环境，不是第三种生命周期模式。

## Capability 与 Tool

Workflow 请求稳定 Capability，而不是直接绑定 Provider。

```text
CapabilityRequirement
→ ToolRegistry
→ compatible ToolAdapter
→ provider execution
```

GUIF 可以注册图片生成、编辑、分割、OCR、Vision、Figma、合成、Visual Diff 和引擎导出 Adapter。没有真实配置凭据、权限、费用和数据流之前，AIPG 不声明 Tool 可用。

## 开发

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

macOS 或 Linux 使用 `.venv/bin/python`。

## 隐私与真实性

真实 Theme、Prompt、源图、会话记录、凭据、私有路径、候选证据和生成产物默认保存在 Framework Git 与 Project Git 之外。公共测试和示例只使用虚构内容。

AIPG 不伪造图片像素、Tool 可用性、语义检查、候选结果或导出成功。

## 兼容策略

AIPG 1.x 保留现有 `guif` 包、命令、Skill、Schema、私有存储变量、Theme 记录、Source 记录、Artifact 记录和 Candidate Change 契约。新的框架级集成使用 AIPG 命名，视觉领域集成可以继续使用 GUIF。

## License

MIT。
