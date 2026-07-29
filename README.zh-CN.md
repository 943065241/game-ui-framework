# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、模型无关的游戏 UI 工作框架，用于规划、指导、形成生产契约、生成 Prompt、审批、执行、审阅、导出和持续演进游戏 UI 工作。

## 当前状态

`v1.0.0-alpha.17` — 已具备 Workflow 驱动的 Runtime Pipeline、确定性的 Planner、Director、Theme、Resource、Prompt 与 Semantic QA Agent、可持久化的 Approval Decision、Provider Adapter 执行门槛、确定性 Dry-run Provider、可持久化 Artifact Record、基于相关性的 Context Selection、可恢复 Task Run、Engine Adapter 导出、确定性校验、保护性编辑，以及 Git-friendly Project Knowledge。

## 产品规格

中英文双语持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。

产品方向、架构、能力状态、兼容性、优先级、风险和验收标准发生变化时，必须在同一个 Release 或 Pull Request 中同步更新该文档。

## 当前可用能力

- `guif init <project>` 创建相互隔离的 Project Workspace。
- `guif run "<requirement>" --project <project>` 解析 Workflow、选择相关 Context、执行 Agent 并保存 Checkpoint。
- `planner` 生成经过校验的 UI Production Plan。
- `director` 审阅 Composition、Hierarchy、Theme Constraint、Resource Reuse、Memory Constraint、Conflict 和 Approval Point。
- `theme` 解析 Active Theme，或生成需要审阅的推导 Theme Contract。
- `resource` 生成经过校验的 Resource Manifest Candidate，同时不会静默修改 Project Truth。
- `prompt` 生成与 Provider 无关的 Prompt IR，其中包含 Job、Constraint、Reference、Output Contract、Blocker、Approval、Capability 和 Provenance。
- `qa` 执行确定性的 Contract QA，并维护显式 Export Gate。
- Approval Decision 会被持久化，并控制 Prompt Job 是否可执行。
- 只有 Task 已完成、Prompt IR 为 `ready`、必要 Approval 已满足、Contract QA 通过且 Provider Capability 匹配时，Provider 才能执行。
- 内置 `dry-run` Provider 不进行外部调用，而是生成确定性的非视觉 Execution Receipt。
- Provider 执行成功后，会登记包含 ID、Path、SHA-256、MIME、Dimension、Provider Metadata、Reference、Output Contract、Approval Snapshot 和 QA State 的 Artifact Record。
- Provider 执行失败会被持久化，不会改变已完成 Task 的 Lifecycle，也不会丢失 Approval History。
- Task Run 可检查，并可在 Pipeline 失败后恢复。
- 已具备 Project、Theme、Workflow、Resource、Image Asset、Protected Pixel 和 Engine Adapter 校验能力。
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

## 端到端 Contract 流程

```text
用户 Requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> 完整 Project Context Snapshot
       -> 基于相关性的 Context Selection
       -> Workflow -> Pipeline
       -> Planner
       -> Director
       -> Theme
       -> Resource
       -> Prompt IR
       -> Semantic Contract QA
       -> Persistent Approval
       -> Provider Adapter
       -> Artifact Registry
       -> 后续 Visual QA / Revision
       -> 后续 Gated Export Agent
```

Runtime 保持与 OpenAI 或其他模型 Provider 解耦。

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "制作 1080x2340 竖屏中世纪港口商店页面并导出 Unity",
    pipeline="ui-production",
)

for approval_id in task.state["approval_state"]["required_ids"]:
    task = runtime.approve(
        "LeekParty",
        task.task_id,
        approval_id,
        actor="reviewer@example.com",
    )

job_id = task.state["prompt_ir"]["jobs"][0]["id"]
task = runtime.execute_job(
    "LeekParty",
    task.task_id,
    job_id,
    provider_id="dry-run",
)

print(runtime.list_artifacts("LeekParty", task.task_id))
```

## Workflow 驱动的 Pipeline

Workflow schema v2 同时声明供人审阅的 Step 与可执行 Agent：

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

Project Workflow 会覆盖同 ID 的 Built-in Workflow。Runtime 会持久化已解析的 Source、Manager、Step 和 Agent Order。如果当前 Agent Order 与已保存 Pipeline 不一致，Resume 会被拒绝。

## Approval Gate

Approval Decision 保存在：

```text
projects/<project>/runs/<task-id>/approvals.json
```

支持：

```text
approved
rejected
changes-requested
```

Gate 行为：

```text
仍有 Pending Approval
  -> Prompt IR: review-required
  -> executable: false

出现 Rejected 或 Changes Requested
  -> Prompt IR: blocked
  -> executable: false

全部必要 Approval 已通过，且没有其他 Blocker
  -> Prompt IR: ready
  -> executable: true
```

Approval 本身不会把 Theme 或 Resource Proposal 写入 Project Truth，也不会自动调用 Provider。Decision History 采用追加记录；最新决定控制当前 Gate。

## Provider Adapter Contract

Provider Adapter 提供模型无关的执行边界：

```text
ExecutionRequest
  -> ProviderAdapter
  -> ExecutionResult
  -> Artifact Registry
```

默认 Registry 当前包含：

```text
dry-run
```

Dry-run Adapter 可用于验证执行 Contract，但它：

- 不进行网络或外部 Provider 调用；
- 不生成图片 Pixel；
- 标记 `simulation: true`、`visual: false`；
- 写入确定性 JSON Execution Receipt；
- 标记 `billable: false`。

Provider 执行前必须同时满足：

1. Runtime Task 为 `completed`；
2. Prompt IR 为 `ready`；
3. Job 为 `executable: true`；
4. Approval Status 为 `approved` 或 `not-required`；
5. Contract QA 为 `passed`；
6. Provider 声明了该 Job 所需的全部 Capability；
7. 要求真实 Reference 的 Provider 已成功绑定 Project File。

## Artifact Registry

执行成功后，Artifact File 保存到：

```text
projects/<project>/runs/<task-id>/artifacts/
```

Registry 保存到：

```text
artifacts.json
executions.json
```

Artifact Record 包含：

```text
artifact_id
job_id 与 artifact_kind
provider、model 与 request metadata
相对文件路径
SHA-256 与字节数
MIME 与 Dimension
simulation 与 visual 标记
Output Contract
已绑定 Reference Record
Approval Snapshot
Prompt Provenance
QA Status
```

登记 Artifact 不代表视觉已经通过。当前 Semantic QA Agent 能识别已登记 Artifact Metadata，但由于尚无 Visual Inspection Adapter，仍会记录 `artifact_review.status: "not-run"`，因此 Export Gate 保持关闭。

## Provider Failure 行为

Provider 调用前会先保存 Checkpoint。失败时会记录：

```text
execution_id
job_id
provider_id
attempt number
request snapshot
exception type 与 message
started_at 与 completed_at
```

Task 继续保持 `completed`，Approval History 不受影响，失败 Attempt 不会登记 Artifact。

## CLI

```bash
guif init LeekParty

guif run "制作 1080x2340 竖屏中世纪港口商店页面并导出 Unity" \
  --project LeekParty \
  --pipeline ui-production

guif run-approval-list <task-id> --project LeekParty
guif run-approve <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com

guif provider-list

guif run-execute <task-id> <job-id> \
  --project LeekParty \
  --provider dry-run

guif run-artifact-list <task-id> --project LeekParty
guif run-artifact-show <task-id> <artifact-id> --project LeekParty

guif run-list --project LeekParty
guif run-show <task-id> --project LeekParty
guif validate LeekParty
```

## 持久化 Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json        存在 Prompt Approval 时
  executions.json       Provider Attempt 后
  artifacts.json        Artifact 登记后
  artifacts/            Artifact File
  error.json            仅 Pipeline 执行失败期间存在
```

`run-list` 会显示 Approval Status、Pending Approval Count、Artifact Count 和 Provider Execution Count。

## 当前限制

- `dry-run` 是唯一内置 Provider，不会调用真实图片模型。
- 尚无 Visual Semantic QA Adapter。
- Artifact Registry 为文件存储，没有 Database、Remote Object Storage 或 Retention Policy。
- Approval Actor 目前只是字符串，不是经过认证的 Host Identity。
- Upstream Contract Hash 变化后，旧 Approval 尚不会自动失效。
- Built-in `export` Agent 仍是 Contract-only，尚未消费 Artifact 与 QA Gate。
- Engine Sidecar 是 GUIF 的确定性 Metadata，不是引擎原生生成的 Import File。

## 运行原则

1. 自然语言是主要用户界面；CLI 用于实现、调试与 CI。
2. Git 与 Project File 是长期事实来源。
3. Runtime 与 Prompt IR 保持 Provider-independent。
4. Workflow Manifest 是 Pipeline Agent Order 的事实来源。
5. Agent 不直接互相调用。
6. 推导 Theme 与 Resource Proposal 必须先审阅，再修改 Project。
7. Prompt Job 必须经过明确 Approval 与 Contract QA 才能调用 Provider。
8. Provider 调用前必须检查 Capability 与 Reference Binding。
9. Provider Failure 必须保留 Task、Approval 与执行证据。
10. Artifact Registration 不等于 Visual QA。
11. Export 必须依赖明确通过的 Artifact 与 QA Gate。
12. Feature、Test、CI、中英文 README、Version Metadata 与 Product Specification 一致时，Release 才算完成。

## 仓库下一步方向

下一优先级为 **alpha.18：Visual Artifact Inspection Contract 与 Revision Planning**。GUIF 需要区分真实视觉 Artifact 与 Simulation，校验图片 Metadata 是否符合 Output Contract，生成结构化 Visual Review Request，并在没有可用 Inspection Adapter 时继续明确保持 `not-run`。具体优先级与验收标准维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。
