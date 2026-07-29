# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，但二者都不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-alpha.22` 新增第一版真正执行生产写入的 **Gated Export Agent**。

现在，Tool 返回图片并不代表它可以直接进入 Project Truth。GUIF 会在任何生产文件写入前检查持久化 Task、初始 Approval、Contract QA、聚合 Visual Review、Active Artifact 身份、已批准 Resource Contract、目标 Engine 兼容性以及 Revision 是否已经解决。

```text
Prompt / Revision Job
  -> Tool 执行或 ChatGPT Handoff
  -> Artifact Registry
  -> Metadata 与 Semantic Visual Review
  -> Active Reviewed Artifact
  -> Gated Export Plan                 不修改 Project
  -> Gated Export Execute
       -> 写入 Project Truth
       -> Engine-specific Export
       -> Export Manifest
       -> Transaction Audit 与 Backup
  -> 可选的冲突检测 Rollback
```

中英文双语持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。

## Export Gate

`Runtime.prepare_gated_export()` 只生成并持久化可审阅计划，不修改任何 Project 文件。

计划检查：

- Task 状态必须为 `completed`；
- 初始 Approval 必须为 `approved` 或 `not-required`；
- Contract QA 必须为 `passed`；
- 聚合 `qa_report.export_gate.allowed` 必须为 true；
- 至少存在一个 Active `production-asset` Artifact；
- 所有选中 Artifact 必须是真实视觉文件、已经通过 Review，并且不是 Simulation；
- Artifact 文件必须仍位于 Run Directory 内，且 SHA-256 与登记记录一致；
- Artifact Output Contract 必须与已批准 Resource Manifest Candidate 完全一致；
- 同一个 Resource 不得存在多个未完成 Supersession 的 Active Artifact；
- 所有 Revision Plan 必须为 `resolved` 或 `rejected`；
- Resource Target 必须兼容目标 Engine。

任何检查失败都会生成并持久化 `blocked` Export Record。GUIF 不会复制生产文件，也不会自动使用其他 Artifact 或 `dry-run` 回退。

## 写入 Project Truth

Ready Export 会把已批准资源写入：

```text
projects/<project>/production-assets/files/<output-name>
projects/<project>/production-assets/<resource-id>.resource.json
```

Materialized Resource Manifest 会指向由 GUIF 管理的 Project Source File。覆盖已有文件前会先创建 Backup。

只有 Active `production-asset` Artifact 会进入 Project Truth。Effect Image、Simulation、Receipt、Stale Artifact 和未完成 Review 的结果只保留作 Provenance，不会进入生产资源集合。

## Engine Export

每次执行都会创建独立输出目录：

```text
projects/<project>/exports/<engine>/<export-id>/
  <approved assets>
  <engine adapter metadata>
  export-manifest.json
```

继续支持 Unity、Godot、Unreal 和 Generic Adapter。Export Manifest 会记录：

- Task 与 Export Identity；
- Target Engine 和 Actor；
- Gate Snapshot；
- Source Artifact、Job、Review 与 SHA-256；
- Project Truth Materialization Path；
- Engine Output Path 与 SHA-256；
- Adapter Output 与 Import Hint。

旧的 `guif export` 命令仍可用于校验并导出已经存在于 Project Truth 中的 Resource 文件。新的 AI 生产流程应使用与 Task 绑定的 Gated Export API。

## Transaction Audit 与 Rollback

每个完成的 Export 都会保存：

```text
projects/<project>/export-history/<export-id>/
  transaction.json
  backups/
```

Transaction 会记录每一次 Project Truth 变更、文件之前是否存在、旧 Hash、Backup Path 和 Export 后 Hash。

Rollback 会检测冲突。GUIF 会比较当前 Project 文件和本次 Export 写入时的 Hash；若文件之后发生过修改，默认 Rollback 会 Fail Closed，避免覆盖更新内容。Force Rollback 必须明确提供 Actor 和 Reason，并写入 Audit。

## Runtime API

```python
runtime = Runtime(workspace)

plan = runtime.prepare_gated_export(
    "LeekParty",
    task_id,
    target_engine="unity",
)

record = runtime.execute_gated_export(
    "LeekParty",
    task_id,
    target_engine="unity",
    actor="project-owner@example.com",
)

exports = runtime.list_gated_exports("LeekParty", task_id)
record = runtime.get_gated_export("LeekParty", task_id, record["export_id"])

rolled_back = runtime.rollback_gated_export(
    "LeekParty",
    task_id,
    record["export_id"],
    actor="project-owner@example.com",
    reason="恢复上一个已批准生产资源集合。",
)
```

## CLI

```bash
guif run-export-plan <task-id> \
  --project LeekParty \
  --target unity

guif run-export-execute <task-id> \
  --project LeekParty \
  --target unity \
  --actor project-owner@example.com

guif run-export-list <task-id> --project LeekParty
guif run-export-show <task-id> <export-id> --project LeekParty

guif run-export-rollback <task-id> <export-id> \
  --project LeekParty \
  --actor project-owner@example.com \
  --reason "恢复上一个已批准生产资源集合。"
```

只有在人工确认 Post-export Conflict 后才应使用 `--force`。

## 持久化状态

Task Run Directory 现在可能包含：

```text
approvals.json
artifacts.json
executions.json
tool-resolution.json
tool-handoffs.json
visual-reviews.json
revision-plans.json
revision-execution.json
gated-exports.json
```

`run-list` 新增 `gated_export_count`、`completed_export_count` 和 `latest_export_status`。

## 已有生产能力

GUIF 还包括：

- Workflow-driven Planner、Director、Theme、Resource、Prompt 和 Semantic QA Agent；
- 基于相关性的 Project Context Selection；
- 持久化 Initial Approval 与 Revision Approval；
- Host 与 Tool 可配置，默认使用 ChatGPT；
- Registered、Available、Installable Tool Discovery；
- 可审阅 Tool Connection Request 与 Opaque Credential Reference；
- ChatGPT 图片生成和修图 External Handoff；
- Artifact Identity、Provenance、SHA-256、MIME、Dimension 与 Reference；
- Deterministic Metadata Review 与可选 Semantic Visual Inspector；
- Immutable Source Binding、独立 Approval 和 Review-gated Supersession 的 Controlled Revision；
- Protected Pixel Composition Check；
- 旧版 Deterministic Resource Export。

## 开发

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

- ChatGPT 产品侧仍需要自动消费 External Handoff 并提交文件；
- 默认 Semantic Visual Inspector Registry 仍为空；
- 当前 Gated Export 只 Materialize 生成的 `production-asset` Artifact，已批准复用 Resource 的统一打包属于后续扩展；
- Rollback 目前基于文件，不会自动创建 Git Branch 或 Commit；
- Export Actor 仍是字符串，不是经过认证的 Host Identity；
- Remote Object Storage、Retention、并发 Export Lock 和 Signed Manifest 尚未实现。

## 下一阶段

下一优先级是 **alpha.23：Authenticated Host API 与 Git Change Management**，包括稳定 Host Result Protocol、Authenticated Actor、Optimistic Concurrency、Git Change Set、Branch、Commit、Rollback Integration、Cancellation 和 Execution Summary。
