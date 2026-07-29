# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、与 Provider 解耦的游戏 UI 工作框架，用于规划、指导、形成生产契约、审批、执行、视觉检查、修订和导出游戏 UI 工作。

## 当前状态

`v1.0.0-alpha.18` 新增 Visual Artifact Inspection Contract 与 Revision Planning。GUIF 现在可以区分真实视觉图片和 Simulation Receipt，验证持久化文件身份，按照 Prompt Output Contract 检查图片 Metadata，生成与 Provider 无关的 Visual Inspection Request，持久化 Visual Review，创建可追溯 Revision Plan，并将被替代的旧 Artifact 标记为 `stale`。

当前生产流程已具备确定性的 Planner、Director、Theme、Resource、Prompt 和 Semantic QA Agent、Persistent Approval Gate、Provider Adapter 执行、Deterministic Dry-run Provider、Artifact Registry、Visual Review Service、可恢复 Task Run、Protected Editing 和 Engine Adapter Metadata Export。

## 产品规格

中英文双语持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。产品方向、架构、能力状态、兼容性、优先级、风险和验收标准发生变化时，必须在同一个 Release 或 Pull Request 中同步更新该文档。

## 当前可执行流程

```text
用户 Requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> Project Context Snapshot 与相关性选择
       -> Workflow -> Pipeline
       -> Planner
       -> Director
       -> Theme Contract
       -> Resource Contract Bundle
       -> Model-neutral Prompt IR
       -> Semantic Contract QA
       -> Persistent Approval Gate
       -> Provider Adapter
       -> Artifact Registry
       -> Visual Review Service
            -> Eligibility 与文件完整性检查
            -> 确定性图片 Metadata 检查
            -> 可选 Visual Inspection Adapter
            -> Revision Plan
       -> 后续 Revision Execution
       -> 后续 Gated Export Agent
```

Runtime 与 Prompt IR 保持与 OpenAI 或其他模型 Provider 解耦。

## 当前可用能力

- `guif init <project>` 创建相互隔离的 Project Workspace。
- `guif run "<requirement>" --project <project>` 解析 Workflow、选择相关 Context、执行 Agent 并保存 Checkpoint。
- Planner、Director、Theme、Resource、Prompt 和 Semantic QA 已经执行真实的确定性领域工作。
- Approval Decision 会持久化，并控制 Prompt Job 是否可执行。
- Provider 只有在 Task、Prompt、Approval、Contract QA、Capability 和 Reference Gate 全部通过后才能执行。
- `dry-run` 不进行外部调用或计费，只生成确定性的非视觉 Execution Receipt。
- Provider 执行成功后会登记 Artifact Identity、File、SHA-256、MIME、Dimension、Provider Metadata、Reference、Output Contract、Approval Snapshot 和 Provenance。
- Visual Review 会区分 Simulation 与真实图片 Artifact。
- 真实图片会检查支持的 MIME、安全的持久化路径、文件存在、SHA-256、Dimension、Format、Alpha 和 Provider 登记 Metadata。
- 与 Provider 无关的 `VisualInspectionRequest` 会携带 Visual Instruction、Negative Constraint、Output Contract、Reference 和 Acceptance Criteria，供兼容 Inspection Adapter 使用。
- 没有 Inspection Adapter 时，Semantic Visual Status 会明确保持 `not-run`；Metadata 校验不会被描述为视觉质量已经通过。
- Visual Finding 可以生成与原 Prompt Job 和 Artifact 关联的 Persistent Revision Plan。
- 同一 Prompt Job 的新 Artifact 可以显式替代旧 Artifact；旧记录变为 `stale`，但 Provenance 会保留。
- Task Run 可检查，并可在 Pipeline Failure 后恢复。
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

图片 Metadata 检查依赖 Pillow，`dev` 与 `image` Extra 均包含该依赖。

## Python API 示例

```python
from pathlib import Path

from guif.runtime import Runtime
from guif.visual_review import VisualReviewService

workspace = Path.cwd()
runtime = Runtime(workspace)

task = runtime.run(
    "LeekParty",
    "制作 1080x2340 竖屏中世纪港口商店页面并面向 Unity",
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

artifact = runtime.list_artifacts("LeekParty", task.task_id)[0]
task = VisualReviewService(workspace).review(
    "LeekParty",
    task.task_id,
    artifact["artifact_id"],
)

print(task.state["qa_report"]["artifact_review"])
```

由于 `dry-run` 生成的是 `simulation: true`、`visual: false`，Review 结果会是 `not-applicable`，而不是视觉通过。

## Approval 与 Provider Gate

Prompt Job 只有同时满足以下条件才可以执行：

```text
Task.status == completed
Prompt IR.status == ready
Job.executable == true
Approval == approved 或 not-required
Contract QA == passed
Provider Capability 满足 Job
必要 Reference File 已绑定
```

Approval 本身不会把推导 Theme 或 Resource Proposal 写入 Project Truth，也不会自动调用 Provider。Provider Attempt 会在调用前保存 Checkpoint；失败时保留 Completed Task、Approval History、Request Snapshot 和 Error Evidence。

## Visual Artifact Eligibility

Visual Review 首先检查 Artifact Record：

```text
状态有效且不是 stale
simulation == false
visual == true
MIME 为 image/png、image/jpeg 或 image/webp
File Path 位于 Run Directory 内
文件实际存在
已登记 SHA-256 与文件字节一致
```

Simulation Receipt 和非视觉文件会得到：

```text
status: not-applicable
visual_conclusion_claimed: false
```

不符合资格或已经损坏的 Visual Artifact 会产生 Blocking Integrity Finding。

## 确定性图片 Metadata Review

对符合资格的图片，GUIF 会检查：

- 实际 Width 与 Height；
- 实际 Image Format；
- Alpha Presence 与 Image Mode；
- 是否符合 Prompt Job 的 `canvas` 和 `output_contract`；
- 是否与 Provider Result 登记的 Dimension 一致。

Metadata 不一致会阻塞 Artifact，并创建 Revision Plan。Metadata 通过本身不代表 Theme、Composition、Content、Readability 或 Usability 已通过。

## Visual Inspection Adapter Contract

Visual Inspection Adapter 会收到：

```text
VisualInspectionRequest
  Task 与 Project Identity
  Artifact 与 Prompt Job Identity
  File Metadata
  Output Contract
  Global Page 与 Theme Contract
  Visual 与 Content Instruction
  Negative Constraint
  Acceptance Criteria
  Required Review Dimension
```

Adapter 需要声明 Capability：

```text
theme-consistency
composition-and-hierarchy
content-correctness
readability
usability
resource-compliance
```

默认 Visual Inspector Registry 有意保持为空。没有选择兼容 Adapter 时，Semantic Review 继续是 `not-run`，Export Gate 继续关闭。

## Revision Plan 与 Artifact Supersession

Blocking、Review 或 Warning Finding 可以创建 Persistent Revision Plan，其中包含：

```text
revision_id
source_job_id
source_artifact_id
finding_ids
revision objectives
preservation constraints
next step
```

Revision Plan 不会覆盖 Source Artifact。替代结果准备完成后，可以显式 Supersede 旧 Artifact。旧记录会变为 `stale` 并指向 `superseded_by`，新记录会保留 `supersedes` 列表。

## CLI

```bash
guif init LeekParty

guif run "制作中世纪港口商店页面并面向 Unity" \
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

guif visual-inspector-list
guif run-artifact-review <task-id> <artifact-id> \
  --project LeekParty

guif run-visual-review-list <task-id> --project LeekParty
guif run-revision-list <task-id> --project LeekParty

guif run-artifact-supersede <task-id> <old-artifact-id> <new-artifact-id> \
  --project LeekParty
```

当 Agent Host 或 Plugin 注册了兼容 Visual Inspection Adapter 后，`run-artifact-review` 可以增加 `--inspector <id>`。默认 CLI Process 没有注册 Semantic Inspector。

## 持久化 Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json          存在 Prompt Approval 时
  executions.json         Provider Attempt 后
  artifacts.json          Artifact 登记后
  visual-reviews.json     Artifact Review 后
  revision-plans.json     提出 Revision 时
  artifacts/              Persistent Artifact File
  error.json              仅 Pipeline 执行失败期间存在
```

`run-list` 会显示 Approval State、Artifact Count、Provider Execution Count、Visual Review Count、Revision Plan Count 和 Aggregate Artifact Review Status。

## 当前限制

- `dry-run` 仍是唯一内置 Provider，不会生成图片 Pixel。
- 默认 Visual Inspector Registry 为空；当前没有 Built-in Model 判断视觉语义。
- Revision Plan 已可持久化，但 Revision Prompt 构建与执行尚未自动化。
- Artifact 使用文件存储，没有 Remote Object Storage、Database 或 Retention Policy。
- Approval Actor 目前只是字符串，不是经过认证的 Host Identity。
- Upstream Contract Hash 变化后，旧 Approval 与 Review 尚不会自动失效。
- Built-in `export` Agent 仍是 Contract-only，尚未消费最终 Artifact 和 Visual QA Gate。

## 运行原则

1. 自然语言是主要入口；CLI 用于实现、调试和 CI。
2. Git 与 Project File 是长期事实来源。
3. Runtime、Prompt IR、Provider Execution 和 Visual Inspection Contract 保持 Provider-independent。
4. 推导 Theme 与 Resource Proposal 必须先 Review，再修改 Project。
5. Prompt Job 必须经过明确 Approval 与 Contract QA 才能调用 Provider。
6. Provider Invocation 前必须执行 Capability 与 Reference Gate。
7. Simulation Receipt 绝不能被描述为 Visual Artifact。
8. Metadata Validation 绝不能被描述为 Semantic Visual Approval。
9. Visual Finding 与 Revision 必须保留 Artifact、Job 和 Approval Provenance。
10. Export 必须依赖 Contract QA 通过，并且所有 Active Visual Artifact 的 Review 通过。
11. Feature、Test、CI、中英文 README、Version Metadata 与 Product Specification 一致时，Release 才算完成。

## 仓库下一步方向

下一优先级为 **alpha.19：Revision Job Construction 与 Controlled Revision Execution**。GUIF 应将已批准 Revision Plan 转换为带版本的 Edit Job，将 Source Artifact 作为不可变 Reference，建立新的 Approval Gate，通过兼容 Editing Provider 执行，并自动关联 Replacement Artifact，同时保留此前全部 Review History。
