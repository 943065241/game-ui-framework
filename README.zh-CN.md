# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT；图片生成、修图、视觉检查、Git Operation 和 Export 都作为可替换 Tool 能力存在。

## 当前状态

`v1.0.0-alpha.20` 首次打通了受控视觉修订闭环。Visual Review Finding 现在可以转换成版本化 Edit Job，拥有独立 Approval Gate，将原 Artifact 作为经过 SHA-256 校验的 Immutable Reference，通过已配置的图片编辑 Tool 执行，登记 Replacement Artifact，自动重新检查 Metadata，并且只有 Replacement 通过 Semantic Visual Review 后才允许替代 Source Artifact。

默认修图 Tool 仍为通过 ChatGPT Host External Handoff 调用的 `chatgpt-image`。GUIF Core 不会假装自己直接生成或修改图片 Pixel。

## 产品规格

中英文双语持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。产品方向、架构、能力状态、兼容性、优先级、风险和验收标准发生变化时，必须在同一个 Release 或 Pull Request 中同步更新该文档。

## 默认生产路径

```text
用户
  -> ChatGPT Host                         默认，可配置
  -> GUIF Runtime
       -> Context Selection
       -> Workflow -> Pipeline
       -> Planner / Director / Theme / Resource
       -> Model-neutral Prompt IR
       -> Contract QA
       -> 初始 Approval Gate
       -> Tool Resolver
       -> 图片生成 Tool
       -> Artifact Registry
       -> Visual Review
            -> Finding
            -> Revision Plan
            -> Versioned Revision Job
            -> 独立 Revision Approval
            -> 图片编辑 Tool
            -> Replacement Artifact
            -> 自动 Metadata Recheck
            -> Semantic Visual Recheck
            -> Gated Supersession
       -> Gated Export
```

ChatGPT 在架构中承担两个相互独立的角色：

- **ChatGPT Host**：负责对话、确认、调度、Tool Invocation 和结果展示；
- **`chatgpt-image` Tool**：通过 Persistent External Callback Handoff 完成图片生成或修图。

二者都是默认值，不是 GUIF Core 的硬编码依赖。

## 受控 Revision Lifecycle

Visual Review 产生的 Revision Plan 本身不能直接执行：

```text
Revision Plan: proposed
  -> 构造 Revision Job
  -> approval-pending
  -> approve / reject / request changes
  -> ready
  -> Tool Resolution
  -> waiting-for-tool-result
  -> Replacement Artifact Registered
  -> 自动 Metadata Review
  -> Semantic Review
  -> 仅 Review Passed 后 Supersede Source
```

### 构造 Revision Job

```python
revision_id = task.state["revision_plans"]["records"][0]["revision_id"]
task = runtime.create_revision_job("LeekParty", task.task_id, revision_id)

revision_job = runtime.list_revision_jobs("LeekParty", task.task_id)[0]
```

Revision Job 会保留原 Prompt Job Contract，并增加：

- `operation: edit`；
- 根据 Visual Finding 生成的 Revision Objective；
- 角色为 `revision-source-artifact` 的 Source Artifact；
- Source Artifact 的 Expected SHA-256；
- Source Job、Source Artifact、Review 和 Revision Plan Provenance；
- 对无关区域和 Protected Region 的保护约束；
- 独立 Revision Approval Point；
- 新建 Artifact 而不是覆盖原文件的要求。

### 独立 Revision Approval

```python
task = runtime.approve_revision(
    "LeekParty",
    task.task_id,
    revision_id,
    actor="art-director@example.com",
    comment="批准执行受控修图。",
)
```

支持：

```text
approved
rejected
changes-requested
```

初始 Production Approval 不会自动授权后续修图。每一个构造出的 Revision Job 都必须拥有独立、可持久化并保留 History 的审批决定。

### ChatGPT 修图 Handoff

```python
task = runtime.execute_revision(
    "LeekParty",
    task.task_id,
    revision_id,
)

handoff = runtime.list_tool_handoffs("LeekParty", task.task_id)[-1]
```

在默认 Project Configuration 下，GUIF 会把 `image-editing` 解析到 `chatgpt-image`。Handoff 包含 Source Image Reference、Revision Objective、Negative Constraint、Preservation Rule、Output Contract、Acceptance Criteria 和 Revision Approval Snapshot。

ChatGPT 完成修图后，由 Host 提交真实文件：

```python
task = runtime.submit_tool_result(
    "LeekParty",
    task.task_id,
    handoff["handoff_id"],
    content=image_bytes,
    filename="shop-page-revision.png",
    mime_type="image/png",
    width=1080,
    height=2340,
    model_id="chatgpt-image",
)
```

GUIF 会登记 Replacement、关联 Source，并立即执行 Eligibility、File Integrity 和 Image Metadata Review。没有 Semantic Inspector 时，状态仍为 `not-run`，Source Artifact 继续保持 Active。

### 受控 Supersession

Replacement 被生成并不代表 Source 立即失效：

```text
Replacement Metadata Passed，Semantic Review Not-run
  -> Source 仍为 registered
  -> Replacement 只是 Candidate

Replacement Semantic Review Passed
  -> Source 变为 stale
  -> Source.superseded_by = Replacement
  -> Replacement.supersedes 包含 Source
  -> Revision Plan 变为 resolved
```

Failed、Blocked 或 Review-required Replacement 会保留完整审计关系，但不能替代 Source。

## Immutable Source Binding

Revision Reference 会保存 Source Artifact File 和 Expected SHA-256。图片编辑 Tool 收到任务前，GUIF 会检查：

```text
Source 位于 Project 内
文件仍然存在
实际 SHA-256 == 已登记 Source SHA-256
Tool 支持 image-editing 与 protected-region-editing
必要 Reference 已绑定
Revision Approval == approved
Contract QA == passed
```

Source 丢失或被修改时，Task 会 Fail Closed 进入 `waiting-for-tool`；GUIF 不会对另一份文件静默执行修图。

## Host 与 Tool 配置

Tool Selection 顺序保持为：

```text
Explicit Tool
  -> Task Override
  -> Project Configuration
  -> Workspace Configuration
  -> Framework Default
```

新 Project 默认配置：

```json
{
  "execution": {
    "schema_version": 1,
    "mode": "production",
    "default_host": "chatgpt",
    "tools": {
      "image-generation": {"primary": "chatgpt-image", "fallback": []},
      "image-editing": {"primary": "chatgpt-image", "fallback": []}
    }
  }
}
```

生产 Tool 缺失或不健康时进入 `waiting-for-tool`。`dry-run` 永远不会成为隐式 Production Fallback。

## CLI

```bash
guif run-revision-list <task-id> --project LeekParty

guif run-revision-create <task-id> <revision-id> \
  --project LeekParty

guif run-revision-approval <task-id> <revision-id> \
  --project LeekParty

guif run-revision-approve <task-id> <revision-id> \
  --project LeekParty \
  --actor art-director@example.com

guif run-revision-execute <task-id> <revision-id> \
  --project LeekParty

guif run-tool-handoff-list <task-id> --project LeekParty

guif run-tool-submit <task-id> <handoff-id> edited.png \
  --project LeekParty \
  --mime-type image/png \
  --width 1080 \
  --height 2340

guif run-artifact-review <task-id> <replacement-artifact-id> \
  --project LeekParty \
  --inspector <inspector-id>
```

通用 Tool 命令继续可用：

```bash
guif host-show
guif tool-list
guif tool-health chatgpt-image --project LeekParty
guif tool-bind image-editing chatgpt-image --project LeekParty
guif tool-scaffold custom-editor image-editing protected-region-editing
```

## Persistent Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json
  tool-resolution.json
  tool-handoffs.json
  executions.json
  artifacts.json
  visual-reviews.json
  revision-plans.json
  revision-execution.json
  artifacts/
  error.json                  仅 Pipeline Execution Failed 时存在
```

`run-list` 会显示 Revision Plan Count、Revision Job Count、Pending Revision Approval Count、Tool Resolution Status、Tool Handoff Count、Artifact Count、Review Count 和 Aggregate Artifact Review Status。

## 现有能力

GUIF 同时具备：

- 确定性的 Planner、Director、Theme、Resource、Prompt 和 Semantic QA Agent；
- Workflow-driven Pipeline 与 Persistent Task Run；
- 基于相关性的 Project Context Selection；
- 初始 Production Approval Decision 与 History；
- Tool Manifest、Registry、Health Check 和 Layered Resolution；
- ChatGPT External Image Handoff 与 Explicit Result Submission；
- Artifact Identity、SHA-256、MIME、Dimension、Reference 和 Provenance；
- Visual Eligibility 与 Deterministic Image Metadata Check；
- 可选 Semantic Visual Inspection Adapter；
- Protected Pixel Composition Check；
- Generic、Unity、Godot 和 Unreal Export Metadata Adapter。

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

## 当前限制

- ChatGPT Host 仍需要产品侧调度来自动消费 Handoff 并提交图片结果；
- 默认 Visual Inspector Registry 为空，Semantic Review 需要 Host 注册 Inspector；
- 当前 Revision Job 以单个 Source Artifact 和单个 Replacement Result 为主，多 Source 与 Mask Package 尚需后续 Contract；
- Tool Installation、Connection、Permission、Cost Disclosure 和 Credential 仍由 Host 管理；
- Artifact 使用 File Store，没有 Remote Object Store 或 Retention Policy；
- Approval Actor 仍是字符串，而不是 Authenticated Host Identity；
- Built-in Export Agent 仍是 Contract-only，尚未 Materialize 最终 Reviewed Artifact Set。

## 运行原则

1. ChatGPT 是默认 Host，不是硬编码依赖。
2. 图片生成和修图是可配置 Tool。
3. 每个 Revision Job 都必须拥有独立 Approval Gate。
4. Revision Source 在 Tool Execution 前必须保持不可变并通过 Hash 校验。
5. Replacement 不得覆盖 Source File。
6. Metadata Review 不等于 Semantic Visual Approval。
7. Supersession 必须依赖 Replacement Review Passed。
8. Tool 或 Source Reference 缺失时必须 Fail Closed。
9. `dry-run` 只能显式用于 Contract Testing。
10. Feature、Test、CI、中英文 README、Version Metadata 与 Product Specification 一致时，Release 才算完成。

## 仓库下一步方向

下一优先级为 **alpha.21：Host / Tool Discovery 与 Connection Workflow**。GUIF 应区分 Registered、Available 和 Installable Tool，持久化 Connection Request，展示 Permission、Data Scope、External Call、Cost 和 Credential 要求，支持 Health Check Retry，并在注册前执行 Plugin Contract Test。
