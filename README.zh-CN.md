# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。它用于规划、指导、形成生产契约、审批、执行、视觉检查、修订和导出游戏 UI 工作，并以 Project File 与 Git 作为长期事实来源。

## 当前状态

`v1.0.0-alpha.19` 将 Host 与 Tool Selection 正式配置化。默认 Host 是 ChatGPT，默认图片生成和修图 Tool 是 `chatgpt-image`。当 Tool 未配置、未注册、不可用或不满足 Capability 时，GUIF 会 Fail Closed，进入可恢复等待状态；生产任务不会静默回退到 `dry-run`。

本版本同时新增 External Tool Handoff、Host Result Submission、分层 Tool Configuration、Tool Manifest、Health Check、Adapter Scaffold，以及 Task schema v3 的 Tool Waiting State。

## 产品规格

中英文双语持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。产品方向、架构、能力状态、兼容性、优先级、风险和验收标准发生变化时，必须在同一个 Release 或 Pull Request 中同步更新该文档。

## 默认产品路径

```text
用户
  -> ChatGPT Host                         默认，可替换
  -> GUIF Runtime
       -> Context Selection
       -> Workflow -> Pipeline
       -> Planner / Director / Theme / Resource
       -> Model-neutral Prompt IR
       -> Contract QA
       -> Persistent Approval Gate
       -> Tool Resolver
            -> chatgpt-image              默认生产 Tool
            -> 其他 Registered Tool       Project / Workspace / Task Override
            -> dry-run                    仅显式测试
       -> External Tool Handoff 或 Direct Execution
       -> Artifact Registry
       -> Visual Review / Revision
       -> Gated Export
```

ChatGPT 在架构中承担两个相互独立的角色：

- **ChatGPT Host**：负责对话、用户确认、调度和结果展示；
- **`chatgpt-image` Tool**：通过 External Callback Handoff 完成图片生成或修图。

二者都是默认值，不是 GUIF Core 的硬编码依赖。未来可以只替换 Host，也可以只替换 Tool。

## Host、Tool 与 Adapter

**Host** 声明当前环境可以提供哪些 Capability。默认 Host Profile 为：

```json
{
  "host_id": "chatgpt",
  "capabilities": [
    "image-generation",
    "image-editing",
    "protected-region-editing",
    "transparent-output",
    "visual-inspection",
    "github-operation"
  ]
}
```

**Tool** 使用版本化 Manifest 声明能力和执行方式：

```json
{
  "tool_id": "chatgpt-image",
  "version": "1.0",
  "execution_mode": "external-callback",
  "capabilities": [
    "image-generation",
    "image-editing",
    "protected-region-editing",
    "transparent-output"
  ],
  "input_contract": "prompt-ir-job-v1",
  "output_contract": "artifact-submission-v1",
  "production_allowed": true
}
```

**Tool Adapter** 将 GUIF 的 Tool Request 转换为：

- Direct Execution Result；或
- 等待 Host 完成后提交文件的 External Handoff。

为了兼容现有代码，显式传入 `provider_id` 时仍可使用 Legacy `ProviderAdapter` 路径；新的产品接口统一使用更宽泛的 Tool 概念。

## 配置优先级

Tool Selection 按以下顺序解析：

```text
本次执行显式指定 Tool
  -> Task Execution Override
  -> Project Configuration
  -> Workspace Configuration
  -> Framework Default
```

新 Project 默认包含：

```json
{
  "execution": {
    "schema_version": 1,
    "mode": "production",
    "default_host": "chatgpt",
    "tools": {
      "image-generation": {
        "primary": "chatgpt-image",
        "fallback": []
      },
      "image-editing": {
        "primary": "chatgpt-image",
        "fallback": []
      }
    }
  }
}
```

Workspace Configuration 可以保存在 `.guif/config.json`。Task 层 Override 可以保存在 `task.state["execution_overrides"]`。

## Tool 未配置时的行为

当所需 Capability 没有配置 Tool、Tool 未注册、Health Check 不通过、当前 Host 不支持，或必要 Reference File 未绑定时，GUIF 不会自动执行 Simulation，而是持久化 Tool Resolution，并把 Task 设置为：

```text
waiting-for-tool
```

Resolution Record 包含：

- 主要 Capability 与完整 Required Capability；
- 选中的 Tool 和配置来源；
- Host 与 Execution Mode；
- Health Check 结果；
- 兼容的 Registered Candidate；
- 失败原因与恢复动作。

用户或 Host 可以：

1. 绑定一个已注册 Tool；
2. 连接或安装其他 Tool；
3. 创建并实现 Adapter Scaffold；
4. 明确选择 `dry-run` 进行 Contract Testing；
5. 取消本次 Pending Execution。

配置完成后，重新执行同一个持久化 Job 即可。Plan、Approval 和已有 Context 不需要重新生成。

## ChatGPT External Handoff

调用 `Runtime.execute_job()` 时不传 `tool_id` 或 `provider_id`，GUIF 会使用配置解析出的 Tool。默认 Project 会创建 `chatgpt-image` Handoff，并把 Task 设置为：

```text
waiting-for-tool-result
```

```python
job_id = task.state["prompt_ir"]["jobs"][0]["id"]
task = runtime.execute_job("LeekParty", task.task_id, job_id)

handoff = runtime.list_tool_handoffs("LeekParty", task.task_id)[0]
```

Handoff 会保留完整 Prompt Job、Bound Reference、Approval Snapshot、Host Action、Safety Constraint 和 Result Submission Contract。

ChatGPT 完成生成或修图后，由 Host 把真实文件提交回 GUIF：

```python
task = runtime.submit_tool_result(
    "LeekParty",
    task.task_id,
    handoff["handoff_id"],
    content=image_bytes,
    filename="shop-page.png",
    mime_type="image/png",
    width=1080,
    height=2340,
    model_id="chatgpt-image",
)
```

GUIF 会校验 Handoff Identity、登记 Artifact、保留 Approval 与 Execution Record、将 Task 恢复为 `completed`，并重新运行 QA。Artifact Registration 仍然不代表视觉质量已经通过。

## `dry-run` 规则

`dry-run` 是确定性的 Contract Testing Tool。它：

- 不进行 External Call；
- 不生成图片 Pixel；
- 不会成为 Production Mode 的自动候选；
- 返回 `simulation: true`、`visual: false`、`billable: false`；
- 在 Production Mode 中只有显式选择时才允许执行。

```python
task = runtime.execute_job(
    "LeekParty",
    task.task_id,
    job_id,
    tool_id="dry-run",
)
```

缺少真实生产 Tool 时，GUIF 绝不会静默改用 `dry-run`。

## Tool Health 与 Adapter Scaffold

```python
runtime.get_host_profile()
runtime.list_tools()
runtime.tool_health("chatgpt-image", project="LeekParty")
runtime.bind_project_tool("LeekParty", "image-generation", "chatgpt-image")
runtime.scaffold_tool(
    "custom-image",
    ("image-generation", "transparent-output"),
)
```

Adapter Scaffold 包含：

```text
tools/<tool-id>/
  tool.json
  adapter.py
  config.schema.json
  README.md
  tests/test_contract.py
```

Scaffold 会明确标记为 `adapter-required` 和 `implementation_ready: false`，不会被自动注册，也不会被视为可用 Tool。

## 现有生产 Contract

GUIF 仍然具备：

- 确定性的 Planner、Director、Theme、Resource、Prompt 和 Semantic QA Agent；
- 基于相关性的 Project Context Selection；
- Persistent Approval Decision 与 History；
- Workflow-driven Pipeline 与 Pipeline Failure Resume；
- Artifact Identity、SHA-256、MIME、Dimension、Reference 和 Provenance；
- Visual Artifact Eligibility 与确定性 Image Metadata Review；
- 可选 Visual Inspection Adapter Contract；
- Persistent Revision Plan 与 Artifact Supersession；
- Protected Pixel Editing Check；
- Generic、Unity、Godot 和 Unreal Export Metadata Adapter。

## CLI

```bash
guif init LeekParty

guif host-show
guif tool-list
guif tool-health chatgpt-image --project LeekParty
guif tool-bind image-generation chatgpt-image --project LeekParty

guif run "制作中世纪港口商店页面并面向 Unity" \
  --project LeekParty \
  --pipeline ui-production

guif run-approve <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com

# 默认：解析 Project Tool 并创建 ChatGPT Handoff
guif run-execute <task-id> <job-id> --project LeekParty

guif run-tool-resolution <task-id> --project LeekParty
guif run-tool-handoff-list <task-id> --project LeekParty

guif run-tool-submit <task-id> <handoff-id> output.png \
  --project LeekParty \
  --mime-type image/png \
  --width 1080 \
  --height 2340

# 只有显式选择时才执行 Simulation
guif run-execute <task-id> <job-id> \
  --project LeekParty \
  --tool dry-run

guif tool-scaffold custom-image image-generation transparent-output
```

Legacy Provider Execution 仍可通过 `--provider <id>` 使用。

## 持久化 Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json
  tool-resolution.json    Tool Resolution 后
  tool-handoffs.json      External Callback Handoff 后
  executions.json         Tool 或 Legacy Provider Attempt 后
  artifacts.json          Artifact Registration 后
  visual-reviews.json
  revision-plans.json
  artifacts/
  error.json              仅 Pipeline Execution 失败期间存在
```

`run-list` 会显示 Tool Resolution Status、Tool Handoff Count、Approval Status、Artifact Count、Execution Count、Visual Review Count、Revision Plan Count 和 Aggregate Artifact Review Status。

## 当前限制

- `chatgpt-image` 是 External Host Bridge；GUIF Core 自身不能直接调用 ChatGPT 图片能力。
- 默认 CLI Process 可以准备 Handoff，但需要 ChatGPT Host 真正生成或编辑图片并提交结果。
- Tool Installation 与 Credential 仍由 Host 管理；alpha.19 会持久化恢复动作，但不会自动安装第三方软件。
- 默认 Visual Inspector Registry 仍为空。
- Revision Plan 已经可以持久化，但 Automatic Revision Job Construction 尚未实现。
- Artifact 使用文件存储，没有 Remote Object Storage、Database 或 Retention Policy。
- Approval Actor 仍是未认证字符串。
- Built-in `export` Agent 仍是 Contract-only，尚未消费最终 Visual QA Gate。

## 运行原则

1. ChatGPT 是默认 Host，但不是硬编码依赖。
2. 图片生成、修图、视觉检查、Git Operation 和 Export 都是可配置 Tool。
3. Tool Resolution 使用 Explicit、Task、Project、Workspace、Framework 的优先级。
4. Tool 缺失或不健康时，Production Execution 必须 Fail Closed。
5. `dry-run` 绝不能成为隐式 Production Fallback。
6. External Tool 完成后必须显式提交 Result。
7. Simulation、Metadata Validation 和 Semantic Visual Approval 必须保持区分。
8. 推导 Theme 与 Resource Proposal 必须先审阅，再修改 Project Truth。
9. Artifact、Approval、Execution、Review 和 Revision Provenance 必须保留。
10. Feature、Test、CI、中英文 README、Version Metadata 与 Product Specification 一致时，Release 才算完成。

## 仓库下一步方向

下一优先级为 **alpha.20：Revision Job Construction 与 Controlled Revision Execution**。GUIF 应将已批准的 Revision Plan 转换为版本化 Edit Job，将 Source Artifact 作为不可变 Reference，建立新的 Approval Gate，通过配置的 `image-editing` Tool 执行，提交 Replacement Artifact，并自动触发 Re-review，同时保留此前全部 Provenance。
