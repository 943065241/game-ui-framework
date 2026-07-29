# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、模型无关的游戏 UI 工作框架，用于规划、生产、审阅、导出和持续演进游戏 UI 工作。

## 当前状态

`v1.0.0-alpha.11` — 已具备由 Workflow 驱动的 Runtime Pipeline、第一个真实可工作的 Structured Planner Agent、可持久化和恢复的 Task Run、Checkpoint 执行、Project Context 加载、Engine Adapter 导出、确定性校验、保护性编辑，以及 Memory、Project、Theme 和 Resource Contract 等基础能力。

## 产品规格

中英文双语的持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。

该文档定义了 GUIF 的产品预期、经验证的当前状态、缺失能力、开发阶段、非目标、风险、待验证问题和验收标准。任何改变 GUIF 产品方向或核心能力状态的迭代，都必须在同一个版本或 Pull Request 中同步更新该文档。

## 当前可用能力

- `guif init <project>` 创建相互隔离的 Project Workspace。
- `guif inspect [project]` 查看 Framework 或 Project 状态摘要，包括已持久化的 Run 数量。
- `guif run "<requirement>" --project <project>` 将 Workflow 解析为 Runtime Pipeline，执行并保存 Checkpoint。
- 内置 `planner` 已经是一个真实的确定性 Agent，会把结构化 UI Production Plan 写入 Task 和 Output Index。
- Project Workflow Manifest 可以覆盖内置 Workflow，并通过 `agents` 声明 Runtime 的执行顺序。
- Workflow schema v1 仍可读取；GUIF 会根据旧版 `manager` 字段推导兼容的 Agent 顺序。
- `guif run-list --project <project>` 列出已持久化的 Task Run。
- `guif run-show <task-id> --project <project>` 加载完整的 Task Snapshot。
- `guif run-resume <task-id> --project <project>` 从可继续执行的 Agent 位置恢复失败或中断的 Task。
- `guif plan "<requirement>"` 为保持兼容，继续保留原有的 Routed Plan JSON 流程。
- `guif validate <project>` 校验 Project 语义、Theme、Workflow 和 Resource Manifest。
- `guif record <type> "<message>"` 保存可复用的 Project Knowledge。
- `guif resource-create`、`resource-show` 和 `resource-validate` 管理 Production Resource Contract。
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
  -> 已解析的 Workflow Manifest
  -> Runtime Pipeline
  -> 已注册的 Agent
  -> 已持久化的 Task 与 Output
```

Runtime 本身不依赖 OpenAI 或任何其他模型提供方。Agent Host 可以直接调用：

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "制作 1080x2340 竖屏中世纪港口商店页面并导出 Unity",
    pipeline="planning",
)
print(task.state["plan"])
```

对应的 CLI 命令：

```bash
guif run "制作 1080x2340 竖屏中世纪港口商店页面并导出 Unity" \
  --project LeekParty \
  --pipeline planning
```

## Workflow 驱动的 Pipeline

Workflow schema v2 同时包含供人审阅的步骤和可执行的 Agent 顺序：

```json
{
  "schema_version": 2,
  "id": "planning",
  "name": "Structured UI Planning",
  "manager": "UI Director",
  "steps": [
    "Convert the requirement and project context into a structured production plan"
  ],
  "agents": ["planner"]
}
```

Runtime 会优先解析 Project Workflow；若不存在，则回退到同 ID 的内置 Workflow。解析后的 Workflow 会直接生成本次执行使用的 Pipeline。其来源、Manager、步骤和 Agent 顺序都会保存到 `Task.state["pipeline"]`，便于审计。

当失败 Task 中保存的 Agent 顺序与当前解析出的 Workflow 不一致时，GUIF 会拒绝 Resume，因为在 Pipeline 已变化的情况下继续执行并不安全。

当前内置可执行 Workflow 包括：

- `ui-production`
- `planning`
- `effect-image`
- `theme-direction`
- `resource-production`
- `quality-assurance`
- `framework-evolution`

## Structured Planner Agent

alpha.11 的 Planner 保持模型无关并采用确定性规则执行，不会调用 LLM。它会把自然语言 Requirement 和当前 Project Context 转换为经过校验的 Plan Schema，其中包括：

- 识别出的 Page Type、Orientation 和 Canvas Dimension；
- Target Engine；
- 当前 Theme Contract、正向要求与排除项；
- 带有原因和评分的可复用 Resource Candidate；
- 建议创建的缺失 Resource Contract；
- Deliverable 和 QA Criteria；
- 有依赖关系的执行步骤；
- Risk、Open Question 和 Context Summary。

Plan 同时存在于：

```python
task.state["plan"]
```

以及已持久化的 Output Index 中：

```text
ui-production-plan
```

这是 GUIF 第一个真正执行领域工作的内置 Agent。`director`、`theme`、`resource`、`prompt`、`qa` 和 `export` 目前仍是 Contract Agent，尚不能自动完成各自预期的生产职责。

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

Pipeline 会在每个 Agent 执行前后保存 Checkpoint。Agent 失败时，GUIF 会记录失败 Agent、异常类型、异常信息和 Retry Index。`run-resume` 会重新加载已保存的 Task，并从该位置继续执行。已经完成的 Task 不能再次恢复。

## Runtime Contract

```text
Runtime
  -> Context Loader
  -> Workflow Resolver
  -> Pipeline
  -> Task Store
  -> Agent Registry
  -> Task + Outputs
```

默认 `ui-production` Workflow：

```text
planner
  -> director
  -> theme
  -> resource
  -> prompt
  -> qa
  -> export
```

每个 Agent 接收并返回同一个可变 `Task`。Agent 之间不直接互相调用；只有 Runtime 会解析并执行 Workflow 中声明的 Agent 顺序。

Runtime Context 当前会加载：

- `project.json`
- 已配置的当前 Project Theme
- Project Workflow Manifest
- Production Resource Manifest
- Project Memory 记录

## 快速开始

```bash
guif init LeekParty

guif run "规划 1080x2340 竖屏中世纪港口商店页面并面向 Unity" \
  --project LeekParty \
  --pipeline planning

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
4. Workflow Manifest 是 Pipeline 执行顺序的事实来源。
5. Agent 不依赖或直接调用其他 Agent。
6. Runtime Run 必须可检查、可持久化并可恢复。
7. Effect Image 与 Production Asset 保持分离。
8. 引擎相关行为属于 Adapter，而不是 Framework Core。
9. 局部编辑通过基于 Mask 的合成保护非目标像素。
10. 只有 Feature、Test、CI、英文 README、中文 README、Version Metadata 和 Product Specification 保持一致时，一次 Release 才算完成。

## 仓库下一步方向

下一优先级是将仅有 Contract 行为的 Director 替换为真实的 Art Direction 与 Resource Reuse Review Agent，然后加入基于相关性的 Context 和 Memory Retrieval。GUIF 后续应继续通过真实 Project Task 验证自然语言生产闭环，而不是扩充更多占位 Interface。具体优先级与验收标准维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。
