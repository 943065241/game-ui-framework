# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、模型无关的游戏 UI 工作框架，用于规划、指导、形成生产契约、生成 Prompt、审阅、审批、导出和持续演进游戏 UI 工作。

## 当前状态

`v1.0.0-alpha.16` — 已具备 Workflow 驱动的 Runtime Pipeline、真实可工作的确定性 Planner、Director、Theme、Resource、Prompt 与 Semantic QA Agent、可持久化的 Approval Decision 与受控 Prompt 状态转换、基于相关性的 Context Selection、可恢复的 Task Run、Engine Adapter 导出、确定性校验、保护性编辑，以及 Git-friendly 的 Project Knowledge。

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
- `resource` 生成经过校验的 Resource Manifest Candidate，同时不会静默修改 Project File。
- `prompt` 生成有版本、与 Provider 无关的 Prompt IR，其中包含 Job、Constraint、Reference、Output Contract、Approval Point、Blocker 和 Provenance。
- `qa` 执行确定性的 Semantic Contract QA，检查跨 Agent 一致性、执行安全和 Export Gate。
- Runtime 会持久化 Approval、Reject 和 Request Changes，并安全控制 Prompt Job 在 `review-required`、`blocked` 和 `ready` 之间转换。
- Approval History 保持可审计，后续新决定可以覆盖当前 Gate，但不会删除历史记录。
- Project Workflow Manifest 可以覆盖 Built-in Workflow，并通过 `agents` 声明可执行顺序。
- Task Run 可持久化、检查、失败恢复，并在 Run List 中显示 Approval 状态。
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
       -> Semantic QA
       -> Export Contract
  -> 已持久化的 Task 与 Output
  -> Human / Host Approval Decision
  -> 受控刷新 Prompt 与 QA 状态
  -> 只有全部必要 Approval 通过后，Job 才能执行
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
print(task.state["prompt_ir"])
print(task.state["qa_report"])

approvals = runtime.get_approvals("LeekParty", task.task_id)
for approval_id in approvals["pending_ids"]:
    task = runtime.approve(
        "LeekParty",
        task.task_id,
        approval_id,
        actor="reviewer@example.com",
        comment="批准进入 Provider 准备阶段。",
    )
```

对应的启动命令：

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
    "Resolve production resource contracts",
    "Build model-neutral generation instructions",
    "Run semantic and technical QA"
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

当前会排序 Markdown Memory Record、Production Resource Manifest 和 Project Workflow Manifest。支持英文 Token 与中文字符 n-gram，常见英文停用词会被过滤，无关记录不会被强行选中。

结果保存在：

```python
task.state["context_selection"]
```

其中包含 Selected Record、Score、Matched Term、Budget、Total Count 和 Omitted Count。Resume 会继续使用已持久化的 Selection，而不是静默读取新的 Project Knowledge。

## Structured Production Agent

### Planner

Planner 会生成 Page Type、Orientation、Canvas Dimension、Target Engine、Active Theme Constraint、Resource Reuse Candidate、Missing Resource Suggestion、Deliverable、QA Criteria、Execution Dependency、Risk、Open Question 和 Context Summary。

```python
task.state["plan"]
```

Output：`ui-production-plan`。

### Director

Director 会生成针对 Page Type 的 Composition Zone、Focal Order、Interaction Hierarchy、相关 Memory Constraint、Resource Reuse Decision、Blocking Conflict、Approval Point 和 Handoff。

状态为 `ready`、`needs-review` 或 `blocked`。

```python
task.state["direction"]
```

Output：`art-direction-review`。

### Theme

Theme Agent 会解析 Active Project Theme；没有 Active Theme 时，可为已识别方向生成需要审阅的确定性 Preset，例如 medieval harbor、natural trading、soft-neon party 或 minimal UI。无法识别的方向保持 `blocked`。Memory Constraint 会合并到 `must_include` 或 `avoid`，互相矛盾的约束会变成显式 Conflict。

```python
task.state["theme_contract"]
```

Output：`resolved-theme-contract`。

推导 Theme 不会自动激活，也不会直接写入 `projects/<project>/themes/`。

### Resource

Resource Agent 会识别已批准复用的 Existing Resource、仍需审阅的 Reuse Candidate、缺失资源的 Validated Manifest Candidate、Dimension Provenance、Engine Import Hint、Blocking Conflict、Approval Point 和 Handoff。

```python
task.state["resource_contracts"]
```

Output：`resource-contract-bundle`。

生成的 Manifest 采用 `review-before-write`。即使 Approval 通过，当前版本也不会自动写入 Project File；后续仍需要独立的 Materialization 操作。

### Prompt

Prompt Agent 会把 Plan、Director Review、Theme Contract 和 Resource Bundle 转换为 Model-neutral Prompt IR。

```python
task.state["prompt_ir"]
```

Output：`model-neutral-prompt-ir`。

Prompt IR schema v1 包含：

- Provider Binding 字段，初始为 `provider_id: null` 与 `model_id: null`；
- 全局 Page、Composition、Theme 和 Negative Constraint Contract；
- 一个 Effect Image Job，以及零个或多个 Production Asset Job；
- Objective、Composition、Visual、Content 和 Technical 等结构化 Instruction Group；
- 已批准的 Resource Reference 和精确 Output Contract；
- 每个 Job 的 Acceptance Criteria；
- Provider Capability Requirement；
- Approval Point、Blocker、Handoff 和完整 Provenance。

只有 Prompt IR 状态为 `ready` 时，Job 才会标记为 `executable: true`。`review-required` 或 `blocked` 的 IR 仍然会保存并可供审阅，但 Provider Adapter 不得自动执行。

### Semantic QA

Semantic QA 会在 Provider 或 Export 之前执行确定性的 Contract 检查：

- Prompt IR Schema 是否有效；
- 上游 Output Provenance Chain 是否完整；
- Plan 与 Prompt IR 的 Page Type、Orientation 和 Canvas 是否一致；
- Theme `must_include` 与 `avoid` 是否完整保留；
- Resource Manifest Candidate 与 Production Asset Job 是否一一对应；
- Resource Output Contract 是否有效且完全一致；
- Reference 是否来自已批准的 Existing Resource；
- Provider Capability Requirement 是否完整；
- Prompt 的 `executable` 状态是否与持久化 Approval State 一致。

```python
task.state["qa_report"]
```

Output：`semantic-qa-report`。

QA 状态为 `passed`、`review-required` 或 `blocked`。当前尚未实现视觉 Semantic QA Adapter。没有登记 Generated Artifact 时，`artifact_review.status` 会保持 `not-run`，即使 Contract Check 全部通过，Export Gate 仍不会打开。

## 持久化 Approval API

每个 Prompt IR 都会初始化：

```python
task.state["approval_state"]
```

Approval 状态包括：

```text
not-required
pending
approved
rejected
changes-requested
```

每次决定会记录 Approval ID、Decision、Actor、可选 Comment、Timestamp、Source 和 Question。每个 Approval ID 的最新决定控制当前 Gate，而 `history` 保持追加式记录，不会因新决定删除旧记录。

受控状态转换规则：

- 未完成的必要 Approval 让 Prompt IR 保持 `review-required`；
- Reject 或 Request Changes 会让 Prompt IR 变为 `blocked`；
- 所有必要 Approval 通过，且没有非 Approval Blocker 时，Prompt IR 变为 `ready`；
- 只有 `ready` 的 Prompt Job 才会变成 `executable: true`；
- 后续把原来的 Reject 或 Request Changes 改为 Approve，可以恢复 Gate；
- 每次 Approval Decision 后都会重新生成 Semantic QA Report；
- Task Lifecycle 仍保持 `completed`，因为 Approval 是 Run 完成后的治理状态；
- Approval 不会修改 Project Theme 或 Resource File，也不会自动调用 Provider。

Runtime API：

```python
runtime.get_approvals(project, task_id)
runtime.approve(project, task_id, approval_id, actor="reviewer", comment="...")
runtime.reject(project, task_id, approval_id, actor="reviewer", comment="...")
runtime.request_changes(project, task_id, approval_id, actor="reviewer", comment="...")
```

CLI：

```bash
guif run-approval-list <task-id> --project LeekParty

guif run-approve <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com \
  --comment "批准"

guif run-reject <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com \
  --comment "构图与需求不一致"

guif run-request-changes <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com \
  --comment "加强主要购买按钮的视觉层级"
```

## 持久化 Task Run

每一次 Runtime 执行都会保存到：

```text
projects/<project>/runs/<task-id>/
```

每个 Run 包含：

```text
task.json       完整 Task Snapshot 和 Lifecycle State
context.json    完整 Project Context Snapshot
events.jsonl    Audit Event
outputs.json    已登记的 Output Index
approvals.json  当前 Approval State 与追加式 Decision History
error.json      Failure Detail，仅在 Task 失败时存在
```

Pipeline 会在每个 Agent 执行前后保存 Checkpoint。Agent 失败时，GUIF 会记录失败 Agent、异常类型、异常信息和 Retry Index。`guif run-resume` 会从该位置继续执行。已完成的 Task 不能再次 Resume，但仍可继续处理 Approval。

`guif run-list` 会包含 `approval_status` 和 `pending_approval_count`。

## 快速开始

```bash
guif init LeekParty

guif run "制作 1080x2340 竖屏中世纪港口商店页面并面向 Unity" \
  --project LeekParty \
  --pipeline ui-production

guif run-list --project LeekParty
guif run-show <task-id> --project LeekParty
guif run-approval-list <task-id> --project LeekParty
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

核心 Exporter 负责校验和暂存资源，Adapter 负责生成 Engine-specific Metadata。

- `generic`：复制通过校验的资源，不生成 Sidecar。
- `unity`：写入 `<asset>.guif-unity.json`。
- `godot`：写入 `<asset>.guif-godot.json`。
- `unreal`：写入 `<asset>.guif-unreal.json`。

这些 JSON Sidecar 是 GUIF 的确定性 Metadata，不是 Engine 原生生成文件。

## 运行原则

1. 自然语言是主要用户界面；CLI 主要用于实现、调试和 CI。
2. Git 与 Project File 是长期事实来源。
3. Runtime 调度保持 Model Agnostic。
4. Workflow Manifest 是 Pipeline Agent Order 的事实来源。
5. Context Selection 必须聚焦、可持久化并可审计。
6. Agent 不直接调用其他 Agent。
7. Runtime Run 必须可检查、可持久化并可恢复。
8. 推导 Theme 与 Resource Proposal 必须 Review Before Write。
9. Approval Decision 必须明确、带 Actor、可持久化，并只能通过新决定修改，不能静默推断。
10. Prompt IR 必须与 Provider 无关，所有必要 Approval 通过后才允许执行。
11. 没有检查真实视觉 Artifact 时，Contract QA 不得声称视觉 QA 已通过。
12. Export 必须通过显式 Export Gate。
13. Effect Image 与 Production Asset 必须分离。
14. Engine-specific 行为属于 Adapter，而不是 Framework Core。
15. 局部编辑通过 Mask Composition 保护非目标像素。
16. 只有 Feature、Test、CI、中英文 README、Version Metadata 和 Product Specification 一致时，一次 Release 才算完成。

## 仓库下一步方向

下一优先级是 Provider Adapter 与 Artifact Registration Contract。它只能消费已经批准且 `executable: true` 的 Prompt Job，必须保留 Structured Constraint 与 Provenance，记录 Capability 和 Execution Metadata，并且不能绕过 Approval 或 Semantic QA Gate。Artifact Registration 稳定后，再继续视觉 Semantic QA、Revision Loop 和真实 Export Agent。具体优先级与验收标准维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。
