# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、模型无关的游戏 UI 工作框架，用于规划、生产、审阅、导出和持续演进游戏 UI 工作。

## 当前状态

`v1.0.0-alpha.10` — 已具备可持久化和恢复的 Runtime Task Run、Pipeline Checkpoint、可组合 Agent、Project Context 加载、Engine Adapter 导出、确定性校验、保护性编辑、Memory、Workflow、Project 和 Theme 等基础能力。

## 产品规格

中英文双语的持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。

该文档定义了 GUIF 的产品预期、经验证的当前状态、缺失能力、开发阶段、非目标、风险、待验证问题和验收标准。任何改变 GUIF 产品方向或核心能力状态的迭代，都必须在同一个版本或 Pull Request 中同步更新该文档。

## 当前可用能力

- `guif init <project>` 创建相互隔离的 Project Workspace。
- `guif inspect [project]` 查看 Framework 或 Project 状态摘要，包括已持久化 Run 的数量。
- `guif run "<requirement>" --project <project>` 执行 Runtime Pipeline 并保存 Checkpoint。
- `guif run-list --project <project>` 列出已持久化的 Task Run。
- `guif run-show <task-id> --project <project>` 加载完整的 Task Snapshot。
- `guif run-resume <task-id> --project <project>` 从可继续执行的 Agent 位置恢复失败或中断的 Task。
- `guif plan "<requirement>"` 生成现有的路由计划格式。
- `guif validate <project>` 校验 Project 语义、Theme、Workflow 和 Resource Manifest。
- `guif record <type> "<message>"` 保存可复用的 Project Knowledge。
- `guif resource-create`、`resource-show` 和 `resource-validate` 管理 Production Contract。
- `guif asset-validate <manifest> <asset>` 检查尺寸、格式、Alpha 和命名。
- `guif export <project> --target <engine>` 通过 Engine Adapter 校验、复制并准备资源。
- `guif compose-edit` 和 `guif qa-pixels` 用于保护并验证非目标像素。
- Test Suite 的目标 Python 版本为 3.10、3.11 和 3.12。

## 开发环境安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## 面向 ChatGPT 的 Runtime 流程

GUIF 的预期主要入口，是通过 ChatGPT 或其他 Agent Host 接收自然语言任务：

```text
用户需求
  -> ChatGPT / Agent Host
  -> GUIF Runtime
  -> Project Context Snapshot
  -> 已选择的 Pipeline
  -> 已注册的 Agent
  -> 已持久化的 Task 结果
```

Runtime 本身不依赖 OpenAI 或任何其他模型提供方。Agent Host 可以直接调用：

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "制作中世纪港口商店页面",
    pipeline="ui-production",
)
print(task.task_id)
print(task.to_dict())
```

对应的 CLI 命令：

```bash
guif run "制作中世纪港口商店页面" \
  --project LeekParty \
  --pipeline ui-production
```

## 持久化 Task Run

每一次 Runtime 执行都会保存到：

```text
projects/<project>/runs/<task-id>/
```

每个 Run 包含：

```text
task.json       完整 Task Snapshot 和生命周期状态
context.json    本次 Run 使用的 Project Context Snapshot
events.jsonl    审计事件记录
outputs.json    已登记的 Output Index
error.json      失败详情，仅在 Task 失败时存在
```

Pipeline 会在每个 Agent 执行前后保存 Checkpoint。Agent 失败时，GUIF 会记录失败 Agent、异常类型、异常信息和需要重新执行的位置。`run-resume` 会重新加载已保存的 Task，并从该位置继续执行。已经完成的 Task 不能再次恢复。

## Runtime Contract

```text
Runtime
  -> Context Loader
  -> Task Store
  -> Pipeline
  -> Agent Registry
  -> Task
```

默认 `ui-production` Pipeline：

```text
planner
  -> director
  -> theme
  -> resource
  -> prompt
  -> qa
  -> export
```

每个 Agent 接收并返回同一个可变 `Task`。Agent 之间不直接互相调用；只有 Runtime 通过 Registry 解析 Pipeline 的执行顺序。

当前内置 Agent 仍只执行 Contract 层行为，包括记录生命周期事件、职责和状态变化。它们还不能完成真实的语义规划、图片生成、视觉审阅或自动化生产。

Runtime Context 当前会加载：

- `project.json`
- 已配置的当前 Project Theme
- Project Workflow Manifest
- Production Resource Manifest
- Project Memory 记录

## 快速开始

```bash
guif init LeekParty
guif run "制作交易按钮" --project LeekParty
guif run-list --project LeekParty
guif run-show <task-id> --project LeekParty

guif resource-create trade-button-long button 264 134 png \
  --project LeekParty \
  --target-engine unity \
  --source source/trade-button-long.png \
  --import-settings '{"spriteMode":"Single","mipmapEnabled":false}'

guif export LeekParty --target unity
guif validate LeekParty
```

## Engine Adapter 层

通用 Exporter 会将引擎相关的准备工作交给不同 Adapter：

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

Adapter Registry 位于 `guif/adapters/`。核心 Exporter 负责校验和暂存资源；Adapter 负责生成引擎相关元数据。

当前行为：

- `generic`：复制通过校验的资源，不生成 Sidecar。
- `unity`：写入 `<asset>.guif-unity.json`，包含 Sprite 和 Mipmap 导入提示。
- `godot`：写入 `<asset>.guif-godot.json`，包含 Texture 导入提示。
- `unreal`：写入 `<asset>.guif-unreal.json`，包含 UI Texture Group 和 Mipmap 提示。

这些 JSON Sidecar 是 GUIF 生成的确定性元数据，不是各引擎原生生成的文件。

## 运行原则

1. 自然语言是主要用户界面；CLI 主要作为实现、调试和 CI 接口。
2. Git 与 Project File 是长期事实来源。
3. Runtime 调度保持模型无关。
4. Agent 不依赖或直接调用其他 Agent。
5. Runtime Run 必须可检查、可持久化并可恢复。
6. Effect Image 与 Production Asset 保持分离。
7. 引擎相关行为属于 Adapter，而不是 Framework Core。
8. 局部编辑通过基于 Mask 的合成保护非目标像素。
9. 只有 Feature、Test、CI、英文 README、中文 README、Version Metadata 和 Product Specification 保持一致时，一次发布才算完成。

## 仓库下一步方向

下一优先级是实现真实的 Structured Planner Agent，并统一 Runtime Pipeline 与 Project Workflow Manifest 的关系。在继续增加更多占位 Agent 之前，GUIF 必须先证明一条完整的自然语言 UI 生产闭环。具体优先级与验收标准维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。
