# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、模型无关的游戏 UI 工作框架，用于规划、指导、形成生产契约、审阅、导出和持续演进游戏 UI 工作。

## 当前状态

`v1.0.0-alpha.13` — 已具备 Workflow 驱动的 Runtime Pipeline、真实可工作的确定性 Planner、Director、Theme 与 Resource Agent、基于相关性的 Context Selection、可持久化和恢复的 Task Run、Engine Adapter 导出、确定性校验、保护性编辑，以及 Git-friendly 的 Project Knowledge。

## 产品规格

中英文双语的持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。

该文档定义 GUIF 的产品预期、经验证的当前状态、缺失能力、开发阶段、非目标、风险、待验证问题和验收标准。产品方向、架构、核心能力状态、兼容性或优先级发生变化时，必须在同一个 Release 或 Pull Request 中同步更新该文档。

## 当前可用能力

- `guif init <project>` 创建相互隔离的 Project Workspace。
- `guif inspect [project]` 查看 Framework 或 Project 状态摘要。
- `guif run "<requirement>" --project <project>` 解析 Workflow、选择相关 Context、执行 Agent 并保存 Checkpoint。
- `planner` 生成经过校验的结构化 UI Production Plan。
- `director` 审阅 Composition、Hierarchy、Theme Constraint、Resource Reuse、Memory Constraint、Conflict 和 Approval Point。
- `theme` 解析 Active Project Theme，或生成需要人工审阅的推导 Theme Contract。
- `resource` 将 Plan 和 Director Decision 转换为经过校验的 Resource Manifest Candidate，同时不会静默修改 Project File。
- Runtime 会依据当前 Requirement 与 Active Theme，对 Project Memory、Resource Manifest 和 Project Workflow Manifest 做相关性排序。
- Project Workflow Manifest 可以覆盖 Built-in Workflow，并通过 `agents` 声明可执行顺序。
- Workflow schema v1 仍可通过旧版 `manager` 映射读取。
- Task Run 可持久化、检查，并可在失败后恢复。
- 已具备 Project、Theme、Workflow、Resource、Image Asset、Pixel Protection 和 Engine Adapter 校验能力。
- Test Suite 覆盖 Python 3.10、3.11 和 3.12。

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

```text
用户 Requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
  -> 完整 Project Context Snapshot
  -> 基于相关性的 Context Selection
  -> 已解析的 Workflow Manifest
  -> Runtime Pipeline
       -> Planner
       -> Director
       -> Theme
       -> Resource
       -> Prompt
       -> QA
       -> Export
  -> 已持久化的 Task 与 Output
```

Runtime 本身不依赖 OpenAI 或任何其他模型提供方。Agent Host 可以直接调用：

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "制作 1080x2340 竖屏中世纪港口商店页面，复用 purchase button，并导出 Unity",
    pipeline="ui-production",
)

print(task.state["plan"])
print(task.state["direction"])
print(task.state["theme_contract"])
print(task.state["resource_contracts"])
```

对应的 CLI 命令：

```bash
guif run "制作 1080x2340 竖屏中世纪港口商店页面，复用 purchase button，并导出 Unity" \
  --project LeekParty \
  --pipeline ui-production
```

## Workflow 驱动的 Pipeline

Workflow schema v2 同时包含供人审阅的步骤与可执行 Agent 顺序：

```json
{
  "schema_version": 2,
  "id": "ui-production",
  "name": "Complete UI Production",
  "manager": "UI Director",
  "steps": [
    "Create a structured UI production plan",
    "Review art direction and resource reuse",
    "Resolve theme constraints",
    "Resolve production resource contracts"
  ],
  "agents": ["planner", "director", "theme", "resource", "prompt", "qa", "export"]
}
```

Runtime 会优先解析 Project Workflow；若不存在，则回退到同 ID 的 Built-in Workflow。Source、Manager、Step 和 Agent Order 会保存到 `Task.state["pipeline"]`。

如果已持久化 Task 的 Agent Order 与当前 Workflow 不一致，GUIF 会拒绝 Resume，避免在 Pipeline 已变化的情况下继续执行。

当前 Built-in Workflow：

- `ui-production`
- `planning`
- `effect-image`
- `theme-direction`
- `resource-production`
- `quality-assurance`
- `framework-evolution`

## 基于相关性的 Context Selection

Runtime 会先加载完整 Project Context Snapshot，再针对当前 Requirement 创建确定性、受预算控制的 Context Selection。

当前会排序：

- `memory/**/*.md` 中的 Markdown Memory Record；
- Production Resource Manifest；
- Project Workflow Manifest。

支持英文 Token 与中文字符 n-gram。常见英文停用词会被过滤，无关记录不会被强行选中。结果保存在：

```python
task.state["context_selection"]
```

其中包含 Selected Record、Score、Matched Term、Budget、Total Count 和 Omitted Count。Resume 会继续使用已持久化的 Selection，而不是静默读取新的 Project Knowledge。

## Structured Planner Agent

Planner 会生成：

- Page Type、Orientation 和 Canvas Dimension；
- Target Engine；
- Active Theme 信息和 Constraint；
- 带有 Score 和 Reason 的 Resource Reuse Candidate；
- Missing Resource Suggestion；
- Deliverable 和 QA Criteria；
- Execution Dependency；
- Risk、Open Question 和 Context Summary。

输出：

```python
task.state["plan"]
```

```text
ui-production-plan
```

## Structured Director Agent

Director 会消费 Plan，并生成：

- 针对 Page Type 的 Composition Zone；
- Focal Order 和 Interaction Hierarchy；
- Theme 的 Palette、Material、Lighting、Must Include 和 Avoid；
- 相关 Memory Constraint；
- Resource Reuse Decision；
- Blocking Conflict 和 Approval Point；
- 面向后续 Agent 的 Handoff。

状态为 `ready`、`needs-review` 或 `blocked`。

输出：

```python
task.state["direction"]
```

```text
art-direction-review
```

## Structured Theme Agent

Theme Agent 会消费 Plan 与 Director Review。

存在 Active Project Theme 时，它会生成经过校验的 `ready` Contract。不存在 Active Theme 时，它可以针对已识别方向生成需要审阅的确定性 Preset，例如：

- medieval harbor；
- natural trading；
- soft-neon party；
- minimal UI。

无法识别的方向会保持 `blocked`，不会虚构生产参数。相关 Memory Constraint 会合并到 `must_include` 或 `avoid`，互相冲突的 Constraint 会显式标记为 Blocking Conflict。

输出：

```python
task.state["theme_contract"]
```

```text
resolved-theme-contract
```

Theme Contract 状态：

```text
ready
review-required
blocked
```

推导出的 Theme 不会自动激活，也不会直接写入 `projects/<project>/themes/`，必须经过明确审阅。

## Structured Resource Agent

Resource Agent 会消费 Plan、Director Review、Theme Contract 和 Project Resource Manifest，并生成：

- 已批准复用的 Existing Resource；
- 仍需审阅的 Reuse Candidate；
- 缺失资源对应的、经过校验的 Resource Manifest Candidate；
- 带有 `plan`、`canvas` 或 `layout-proposal` 来源的尺寸建议；
- Engine-specific Import Hint；
- Unresolved Item、Blocking Conflict 和 Approval Point；
- 面向 Prompt、QA 和 Export 的 Handoff。

输出：

```python
task.state["resource_contracts"]
```

```text
resource-contract-bundle
```

生成的 Manifest 符合现有 Resource Schema，但 Runtime 采用 `review-before-write` Policy，不会在没有明确批准时创建或覆盖 Project Resource File，避免把确定性布局建议直接变成未经审阅的生产事实。

## 持久化 Task Run

每次 Runtime 执行都会保存到：

```text
projects/<project>/runs/<task-id>/
```

每个 Run 包含：

```text
task.json       完整 Task Snapshot 和 Lifecycle State
context.json    完整 Project Context Snapshot
events.jsonl    Audit Event
outputs.json    Output Index
error.json      Failure Detail，仅失败时存在
```

Pipeline 会在每个 Agent 执行前后保存 Checkpoint。失败时会记录 Agent、Exception Type、Message 和 Retry Index。`guif run-resume` 会从该位置继续执行。已完成 Task 不能再次 Resume。

## 快速开始

```bash
guif init LeekParty

guif run "制作 1080x2340 竖屏中世纪港口商店页面并面向 Unity" \
  --project LeekParty \
  --pipeline ui-production

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

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

核心 Exporter 负责校验和暂存资源；Adapter 负责 Engine-specific Metadata。

- `generic`：复制通过校验的资源，不生成 Sidecar。
- `unity`：写入 `<asset>.guif-unity.json`。
- `godot`：写入 `<asset>.guif-godot.json`。
- `unreal`：写入 `<asset>.guif-unreal.json`。

这些 JSON Sidecar 是 GUIF 生成的确定性 Metadata，不是各 Engine 原生生成的文件。

## 运行原则

1. 自然语言是主要用户界面；CLI 主要作为实现、调试和 CI 接口。
2. Git 与 Project File 是长期事实来源。
3. Runtime 调度保持 Model Agnostic。
4. Workflow Manifest 是 Pipeline 执行顺序的事实来源。
5. Context Selection 必须聚焦、持久化并可审计。
6. Agent 不直接调用其他 Agent。
7. Runtime Run 必须可检查、可持久化并可恢复。
8. 推导出的 Theme 与 Resource Proposal 必须先审阅，再修改 Project File。
9. Effect Image 与 Production Asset 保持分离。
10. Engine-specific Behavior 属于 Adapter，而不是 Framework Core。
11. 局部编辑通过 Mask Composition 保护非目标像素。
12. 只有 Feature、Test、CI、中英文 README、Version Metadata 和 Product Specification 一致时，一个 Release 才算完成。

## 仓库下一步方向

下一优先级是实现 Model-neutral Prompt IR Agent，把 Plan、Director、Theme 和 Resource Contract 转换为可版本化、与 Provider 无关的生成指令。只有该 Contract 稳定后，才开始接入 Generation Tool。具体优先级和验收标准维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。
