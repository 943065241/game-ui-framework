# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.22`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF 的产品定位、已验证能力、边界、风险与迭代基线。Feature、Test、CI、中英文 README、Version Metadata 和本文件必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、以自然语言为主要入口、Host 与 Tool 均可配置、以 Project File 与 Git 作为长期事实来源、面向游戏 UI 全生产流程的可执行 AI 工作框架。

默认路径：

```text
用户
  -> ChatGPT Host                         默认，可替换
  -> GUIF Runtime
       -> Project Context / Retrieval
       -> Workflow / Pipeline
       -> Planner / Director / Theme / Resource / Prompt
       -> Contract QA
       -> Initial Approval
       -> Tool Discovery / Connection / Execution
       -> Artifact Registry
       -> Visual Review
       -> Controlled Revision
       -> Gated Export
       -> Project Truth / Engine Output / Audit
```

核心原则：

- ChatGPT-first，但不把 ChatGPT 写死在 Core；
- Tool 可配置，生产任务缺少 Tool 时 Fail Closed；
- 先审批、后执行；先 Review、后 Supersession；
- Artifact 与 Source 通过 SHA-256 保持身份；
- Metadata Review 不冒充 Semantic Visual Review；
- 未通过全部 Gate 的结果不得写入 Project Truth；
- 生产变更必须可审计、可恢复，并避免覆盖后续修改。

### 2. alpha.22 已验证能力

#### 2.1 Gated Export Plan

`Runtime.prepare_gated_export()` 会读取持久化 Task 并生成可审阅 Export Record，不修改 Project 文件。

检查项：

1. Task 为 `completed`；
2. Initial Approval 为 `approved` 或 `not-required`；
3. Contract QA 为 `passed`；
4. 聚合 `qa_report.export_gate.allowed` 为 true；
5. 存在 Active `production-asset` Artifact；
6. Artifact 不是 Simulation，包含真实视觉 Pixel，并且 Visual Review 为 `passed`；
7. Artifact 文件仍位于 Run Directory 内，且 SHA-256 与登记记录一致；
8. Artifact Output Contract 与已批准 Resource Manifest Candidate 一致；
9. 同一个 Resource 只有一个 Active Artifact；
10. 所有 Revision Plan 为 `resolved` 或 `rejected`；
11. Resource Target 与 Export Target Engine 兼容。

任一检查失败：

```text
Export.status = blocked
Project Truth 不变
Engine Output 不创建
```

#### 2.2 Project Truth Materialization

Ready Export 将已批准生产资源写入：

```text
projects/<project>/production-assets/files/<output-name>
projects/<project>/production-assets/<resource-id>.resource.json
```

Materialized Manifest 的 `source` 指向由 GUIF 管理的生产文件。已有文件在覆盖前保存 Backup。

当前只 Materialize Active `production-asset` Artifact。Effect Image、Simulation、Receipt、Stale Artifact 和未完成 Review 的 Artifact 不进入生产集合。

#### 2.3 Engine-specific Export

每次执行创建独立目录：

```text
projects/<project>/exports/<engine>/<export-id>/
  approved assets
  adapter metadata
  export-manifest.json
```

继续支持 Generic、Unity、Godot 和 Unreal Adapter。Manifest 保存：

- Export、Task、Project、Target Engine 和 Actor；
- Gate Snapshot；
- Artifact、Job、Review、Resource 与 SHA-256；
- Project Truth Path；
- Engine Output Path 与 Hash；
- Adapter Result 和 Import Hint。

#### 2.4 Transaction Audit

每次完成的 Export 创建：

```text
projects/<project>/export-history/<export-id>/
  transaction.json
  backups/
```

Transaction 对每个生产变更保存：

- Path；
- 文件之前是否存在；
- Before SHA-256；
- Backup Path；
- After SHA-256；
- Actor 与时间；
- Engine Output 与 Export Manifest。

执行过程发生异常时，GUIF 自动恢复已经写入的 Project 文件并删除不完整 Engine Output。

#### 2.5 Conflict-aware Rollback

Rollback 会在恢复前比较当前文件 Hash 与 Export 写入时的 After Hash。

```text
文件未被后续修改
  -> 安全恢复 Backup 或删除新建文件

文件已被后续修改
  -> 默认拒绝 Rollback
  -> 只有明确 force + actor + reason 才允许继续
```

Rollback 的状态、Actor、Reason、Force 与冲突列表会进入 Task Event、Export Record 和 Transaction Audit。

#### 2.6 Persistence 与 Runtime API

Run Directory 新增：

```text
gated-exports.json
```

`run-list` 新增：

```text
gated_export_count
completed_export_count
latest_export_status
```

Runtime API：

```python
prepare_gated_export(project, task_id, target_engine=None)
execute_gated_export(project, task_id, target_engine=None, actor="host")
list_gated_exports(project, task_id)
get_gated_export(project, task_id, export_id)
rollback_gated_export(project, task_id, export_id, actor=..., reason=..., force=False)
```

CLI：

```text
run-export-plan
run-export-execute
run-export-list
run-export-show
run-export-rollback
```

### 3. 与既有能力的关系

alpha.22 不替代以下能力：

- alpha.16 Initial Approval；
- alpha.17 Artifact Registry；
- alpha.18 Visual Review 与 Revision Plan；
- alpha.19 Configurable Host / Tool 与 ChatGPT Handoff；
- alpha.20 Revision Job、独立 Revision Approval、Immutable Source 与 Gated Supersession；
- alpha.21 Tool Discovery、Connection、Credential Reference、Health Retry 与 Contract Test。

旧版 `guif export` 继续用于已经存在于 Project Truth 的 Resource。Task 产生的 AI Artifact 应通过 Gated Export 才能进入生产文件。

### 4. 当前边界

- 默认 Semantic Visual Inspector Registry 为空；
- ChatGPT 产品侧尚未自动消费 Handoff 并提交结果；
- Gated Export 尚未把 Approved Reuse Resource 与新 Artifact 合并为同一事务；
- Actor 仍是字符串，没有认证和签名；
- Rollback 尚未与 Git Branch、Commit 和 Revert 集成；
- 没有 Remote Object Storage、Retention、Lease 或 Concurrent Export Lock；
- Export Manifest 尚未签名；
- Engine Adapter 仍生成导入 Metadata，不直接操作运行中的 Unity、Godot 或 Unreal Editor。

### 5. 下一阶段

#### alpha.23：Authenticated Host API 与 Git Change Management

- Stable Host Result Protocol；
- Authenticated Host / Approval / Export Actor；
- Optimistic Concurrency 与 Task Lease；
- Git Change Set；
- Branch、Commit、Diff、Revert；
- Export Transaction 与 Git Commit 关联；
- Pause、Cancel、Timeout 和 Result Summary。

#### 后续候选

- Approved Reuse Resource Packaging；
- Multi-source 与 Mask Package Revision；
- Signed Tool / Export Manifest；
- Cost、Latency、Privacy 与 Quality-aware Tool Routing；
- Remote Artifact Store 与 Retention；
- Native Engine Editor Integration。

### 6. 主要风险

- Host Callback 仍依赖产品侧编排；
- Semantic Inspection 的默认责任主体尚未确定；
- 未认证 Actor 无法作为强审计身份；
- 文件系统事务不能完全替代 Git 或数据库事务；
- Force Rollback 可能覆盖后续工作，必须保持显式且可审计；
- Framework 可能继续增加 Contract，而没有缩短真实用户生产路径。

### 7. 迭代记录

- `alpha.9`：Runtime、Task、Agent、Registry、Pipeline Contract。
- `alpha.10`：Persistent Run、Checkpoint、Failure Resume。
- `alpha.11`：Workflow-driven Pipeline 与 Structured Planner。
- `alpha.12`：Structured Director 与 Context Retrieval。
- `alpha.13`：Theme / Resource Agent 与 Review-before-write。
- `alpha.14`：Model-neutral Prompt IR。
- `alpha.15`：Semantic Contract QA。
- `alpha.16`：Persistent Approval 与 Controlled State Transition。
- `alpha.17`：Provider Adapter、Dry-run 与 Artifact Registry。
- `alpha.18`：Visual Artifact Inspection、Revision Plan 与 Supersession。
- `alpha.19`：Configurable Host / Tool、ChatGPT Bridge、Waiting State 与 External Submission。
- `alpha.20`：Revision Job、Independent Approval、Immutable Source 与 Review-gated Supersession。
- `alpha.21`：Host / Tool Discovery、Connection Request、Credential Reference 与 Contract Test。
- `alpha.22`：Gated Export Plan、Project Truth Materialization、Engine Export Manifest、Transaction Audit 与 Conflict-aware Rollback。

---

## English Version

### 0. Purpose

This file is GUIF's living product definition, verified capability review, boundary, risk register, and iteration baseline. Feature implementation, tests, CI, both READMEs, version metadata, and this specification must agree for a release to be complete.

### 1. Product definition

GUIF is a local-first executable AI work framework for end-to-end game UI production. Natural language is the primary interface, Hosts and Tools are configurable, and Project files plus Git are the long-term source of truth.

Default path:

```text
User
  -> ChatGPT Host by default
  -> GUIF Runtime
  -> deterministic production Agents
  -> Contract QA and initial Approval
  -> Tool discovery, connection, and execution
  -> Artifact Registry
  -> Visual Review
  -> controlled Revision
  -> Gated Export
  -> Project truth, Engine output, and audit
```

Core principles:

- ChatGPT-first, not ChatGPT-hard-coded;
- production fail-closed behavior;
- approval before execution and review before supersession;
- SHA-256 Artifact and source identity;
- no false semantic visual claims;
- no Project mutation before every required gate passes;
- auditable and recoverable production changes;
- rollback must not silently overwrite later work.

### 2. Verified state at alpha.22

#### 2.1 Gated Export Plan

`Runtime.prepare_gated_export()` evaluates persisted Task state without mutating Project files.

It requires a completed Task, satisfied initial Approval, passing Contract QA, aggregate Visual Export Gate approval, at least one active production Artifact, real reviewed pixels, valid Run-local path and SHA-256 identity, an exact approved Resource Contract match, unique active Resource identity, resolved or rejected Revision Plans, and Engine compatibility.

A failed check persists a blocked Export record and performs no production write.

#### 2.2 Project truth materialization

A ready Export writes managed assets and Resource manifests under `production-assets/`. Existing files are backed up before replacement. Only active reviewed `production-asset` Artifacts are selected.

#### 2.3 Engine output

Each execution creates `exports/<engine>/<export-id>/` with approved assets, Engine Adapter metadata, and `export-manifest.json`. The manifest captures gate, Artifact, Resource, review, SHA-256, path, actor, and Adapter provenance.

#### 2.4 Audit and rollback

`export-history/<export-id>/transaction.json` records every mutation and backup. Execution failures trigger automatic restoration. Explicit rollback compares current hashes with the hashes written by the Export and fails closed when later Project changes are detected. Force rollback requires an actor and reason and remains auditable.

#### 2.5 APIs and persistence

New Runtime APIs prepare, execute, list, show, and roll back gated Exports. `gated-exports.json` persists Task-bound state, and Run summaries expose Export counts and latest status.

### 3. Compatibility

Alpha.22 builds on persistent Approval, Artifact Registry, Visual Review, configurable Tools, ChatGPT external handoffs, controlled Revision Jobs, immutable source binding, Tool Discovery, Connection Requests, opaque Credential references, Health Retry, and Tool Contract Tests.

The legacy `guif export` command remains available for Resources already present in Project truth. AI-produced Artifacts should use the gated Task-bound path.

### 4. Remaining gaps

- automatic ChatGPT product callback wiring;
- a default semantic Visual Inspector;
- authenticated and signed actors;
- packaging approved reused Resources in the same Export transaction;
- Git branch, commit, and revert integration;
- concurrent Export locking and Task leases;
- remote Artifact storage and retention;
- signed Export manifests;
- native live Engine editor integration.

### 5. Next phase

`alpha.23` will focus on an authenticated Host API and Git change management: stable result protocol, actor identity, optimistic concurrency, leases, Git change sets, branches, commits, diffs, reverts, transaction-to-commit linkage, cancellation, timeouts, and execution summaries.

### 6. Main risks

The main risks are product-side callback dependency, unresolved semantic inspection ownership, weak string actor identity, file transactions without Git or database atomicity, dangerous forced rollback, and interface growth that does not shorten the real user production path.
