# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.20`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅、风险清单和后续迭代基线，不是一次性 Roadmap 或宣传文案。

发生以下变化时，必须在同一个 Release 或 Pull Request 中同步更新本文件：

- 产品定位、边界或核心原则变化；
- Runtime、Task、Agent、Workflow、Context、Host、Tool、Prompt、Approval、Artifact、Visual Review、Revision、QA 或 Export 等核心能力变化；
- 某项能力从 Contract / 占位升级为真实可执行能力；
- CLI、Agent Host 接入方式、Project 目录或数据格式发生兼容性变化；
- 迭代优先级、已知风险或待验证假设变化。

一次 Release 只有在 Feature、Test、CI、中英文 README、Version Metadata 和本文件一致时才算完成。

### 1. GUIF 的预期

#### 1.1 一句话定义

GUIF 是一个以自然语言为主要入口、由可配置 Host 调度、通过可配置 Tool 完成具体工作、以 Git 与 Project File 作为长期事实来源、面向游戏 UI 生产全过程的可执行 AI 工作框架。

#### 1.2 默认产品路径

```text
用户
  -> ChatGPT Host                         默认，可替换
  -> GUIF Runtime
       -> Project Context 与相关性选择
       -> Workflow -> Pipeline
       -> Planner / Director / Theme / Resource
       -> Model-neutral Prompt IR
       -> Contract QA
       -> Persistent Approval Gate
       -> Tool Resolver
            -> chatgpt-image              默认图片生成与修图 Tool
            -> 其他 Registered Tool       可配置替换
            -> dry-run                    仅显式测试
       -> External Handoff 或 Direct Execution
       -> Artifact Registry
       -> Visual Review
            -> Finding
            -> Revision Plan
            -> Revision Job
            -> 独立 Revision Approval
            -> Image Editing Tool
            -> Replacement Artifact
            -> Re-review
            -> Gated Supersession
       -> Gated Export
```

ChatGPT 在默认路径中承担两个独立角色：

- **ChatGPT Host**：负责对话、意图确认、审批交互、调度与结果展示；
- **`chatgpt-image` Tool**：负责真正的图片生成与修图，并通过 External Callback 将结果提交回 GUIF。

GUIF Core 不硬编码依赖 ChatGPT。Host 与 Tool 都可以按 Framework、Workspace、Project、Task 或单次执行层级替换。

#### 1.3 核心价值

- **自然语言优先**：用户表达目标，Framework 负责拆解、约束、执行和解释。
- **可执行而非 Prompt Collection**：GUIF 必须产生 Task、Plan、Contract、Approval、Handoff、Artifact、Review 和 Revision。
- **Host / Tool Configurable**：对话入口和具体执行能力都可替换。
- **ChatGPT Default**：默认使用 ChatGPT Host 与 ChatGPT 图片能力，降低首次使用门槛。
- **Project Isolation**：不同游戏的 Theme、Resource、Memory、Run 和 Artifact 互不污染。
- **Deterministic Contract**：Naming、Dimension、Alpha、Hash、State Transition、Validation 和 Export 尽可能可重复。
- **可审计、可恢复**：每次 Run 必须说明输入、Context、Decision、Tool Resolution、Execution、Artifact、Failure 和下一步。
- **Review Before Write / Execute**：未经批准不得把推导结果写入 Project Truth 或调用生产 Tool。
- **Fail Closed**：生产任务缺少 Tool、Reference 或 Approval 时必须暂停。
- **No False Verification**：Simulation、Metadata Check 和 Visual Semantic Review 必须明确区分。
- **Immutable Provenance**：Revision 不覆盖原 Artifact；Replacement 通过 Review 后才建立 Supersession。

#### 1.4 目标架构

```text
User
  -> Host Registry
       -> ChatGPT Host                    default
       -> CLI / Service / Custom Host
  -> GUIF Runtime
       -> Context Loader / Retrieval
       -> Workflow Resolver / Pipeline
       -> Agent Registry
       -> Initial Approval Gate
       -> Tool Resolver
            -> Tool Registry / Manifest / Health
            -> Direct Tool Adapter
            -> External Callback Tool Adapter
       -> Tool Handoff / Result Submission
       -> Artifact Registry
       -> Visual Review Service
       -> Revision Planner
       -> Revision Job Builder
       -> Revision Approval Gate
       -> Revision Tool Execution
       -> Replacement Review / Supersession
       -> Export Gate
       -> Task Store / Git Change Management
```

职责边界：

- **Host**：理解对话、声明环境能力、处理用户确认、选择 Tool 并提交 External Result。
- **Runtime**：执行 Workflow、维护 Task Lifecycle、协调 Approval、Tool Resolution、Execution 和 Artifact State Transition。
- **Tool Manifest**：声明 ID、Version、Capability、Execution Mode、Environment、Credential、Host Support 和 I/O Contract。
- **Tool Resolver**：按 Explicit、Task、Project、Workspace、Framework 顺序解析 Tool。
- **Tool Adapter**：将 Tool Request 转换为 Direct Result 或 External Handoff。
- **Artifact Registry**：保存 File、Hash、MIME、Dimension、Tool Metadata、Approval Snapshot 和 Provenance。
- **Visual Review Service**：执行 Eligibility、Integrity、Metadata 和可选 Semantic Review。
- **Revision Plan**：将 Finding 关联到 Source Job 和 Source Artifact。
- **Revision Job**：将 Revision Plan 转换为受控 Edit Contract；绑定不可变 Source；拥有独立 Approval。
- **Supersession Gate**：Replacement Review 通过前，Source 必须继续 Active。
- **Export Gate**：只有 Contract QA 与所有 Active Visual Artifact Review 通过时才允许真实 Export。

#### 1.5 非目标

GUIF 不计划：

- 替代 Photoshop、Figma、Unity、Godot 或 Unreal；
- 管理完整游戏逻辑、Server、数值或关卡代码；
- 训练基础模型；
- 成为任意行业的通用 Agent Framework；
- 自动安装未知第三方软件或静默保存 Credentials；
- 把 Dry-run Receipt 描述为图片；
- 把 Dimension / Format / Alpha Check 描述为视觉美术质量通过；
- 在缺少生产 Tool 时自动使用 Simulation；
- 使用初始 Production Approval 自动授权后续 Revision；
- 在 Replacement Review 通过前覆盖、删除或停用 Source Artifact。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.20` 仓库代码。

状态定义：

- **可用**：已经能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：目标明确，但仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录、`project.json`、`runs/` 与默认 ChatGPT Execution Config | Migration、Template、Archive、Schema Upgrade |
| Workflow / Pipeline | 基础可用 | Workflow-driven、Project Override、Checkpoint、Resume | Branch、Concurrency、Skip、Cancel、Policy Retry |
| Planner / Director / Theme / Resource / Prompt | 基础可用 | 真实确定性 Agent，生成 Plan、Direction、Theme Contract、Resource Bundle 和 Prompt IR | 复杂 Page Tree、Interaction Flow、Reference Image Review |
| Semantic Contract QA | 基础可用 | 校验 Prompt、Theme、Resource、Approval、Capability 与执行安全 | Cross-page、Usability 和默认 Visual Semantic QA |
| Initial Approval | 基础可用 | Approve / Reject / Request Changes、History、Prompt Gate、QA Refresh | Authenticated Identity、Role、Expiry、Contract Hash Invalidation |
| Host Profile | 基础可用 | 默认 `chatgpt`，声明 Generation、Editing、Inspection 与 Git Capability | Discovery Protocol、Authenticated Identity、Multiple Hosts |
| Tool Manifest / Registry | 基础可用 | 注册 `chatgpt-image` 与 `dry-run`；声明 Capability、Execution Mode 和 Production Policy | Dynamic Plugin Loading、Signature、Distribution |
| Tool Resolution | 基础可用 | Explicit -> Task -> Project -> Workspace -> Framework；Fail Closed | Cost / Latency / Privacy Policy、Multi-tool Composition |
| ChatGPT Image Bridge | 基础可用 | External Callback Handoff 与 Result Submission | ChatGPT Product-side Automatic Callback、Progress |
| Task / Store | 基础可用 | Task schema v3；Tool Waiting、Handoff、Artifact、Review 与 Revision 持久化 | Migration、Diff、Replay、Optimistic Lock |
| Artifact Registry | 基础可用 | ID、File、SHA-256、MIME、Dimension、Reference、Approval、QA、Provenance | Remote Store、Retention、Signing |
| Visual Review | 基础可用 | Eligibility、Integrity、Metadata、可选 Inspector、Revision Plan | 默认 Inspector、Cross-page Review、Human Review UI |
| Revision Job Builder | 可用 | Plan -> Versioned Edit Job；Objective、Constraint、Output、Provenance | Mask Package、Multi-source、Partial Region Schema |
| Revision Source Binding | 可用 | Source 作为 Immutable Reference；执行前校验 Project Path、File 和 Expected SHA-256 | Remote Artifact Binding、Signed Reference |
| Revision Approval | 可用 | 独立 Approve / Reject / Request Changes 与 History | Authenticated Role、Expiry、Hash Invalidation |
| Revision Tool Execution | 基础可用 | 使用 Configured `image-editing` Tool；默认 ChatGPT Handoff；支持 Waiting State | Streaming、Cancel Callback、Multiple Replacement Candidates |
| Replacement Re-review | 基础可用 | Result Registration 后自动 Eligibility / Integrity / Metadata Recheck | 自动选择 Semantic Inspector、Human Review Queue |
| Gated Supersession | 可用 | Replacement Review Passed 后自动 Source -> stale；失败或 Not-run 不替代 | Merge / Branch Supersession、Multi-variant Selection |
| Adapter Scaffold | 基础可用 | 生成 Manifest、Adapter、Schema、README 与 Test Scaffold | Contract Test Runner、Packaging、Installation |
| Export | 基础可用 | Generic / Unity / Godot / Unreal Metadata Adapter | Export Agent 仍 Contract-only；未消费最终 Artifact Gate |
| Git Change Management | 未开发 | Git 是原则，但 Runtime 不管理 Commit Lifecycle | Change Set、Branch、Commit、Rollback、Approval |

#### 2.1 当前可真实完成的闭环

```text
Project Init
-> Requirement -> Plan / Direction / Theme / Resource / Prompt
-> Contract QA -> Initial Approval
-> Tool Resolution -> ChatGPT Handoff
-> Host Result Submission -> Artifact Registration
-> Visual Review -> Revision Plan
-> Revision Job Construction
-> Independent Revision Approval
-> Image Editing Handoff
-> Replacement Submission
-> Automatic Metadata Recheck
-> Semantic Recheck
-> Passing Replacement Supersedes Source
```

#### 2.2 当前关键边界

GUIF Core 仍不能主动调用 ChatGPT Product 内的图片工具。它准备 Handoff、持久化 Contract 并接收结果；ChatGPT Host 必须执行图片生成或修图并提交真实文件。

自动 Re-review 当前必定执行 Eligibility、Integrity 和 Metadata 检查；Semantic Review 仍需要注册 Inspector。没有 Inspector 时 Replacement 状态保持 `not-run`，Source 不会被 Supersede。

Revision Job 当前以单个 Source Artifact 为主。Mask、多个 Reference Artifact、局部目标区域和多候选选择尚未形成正式 Contract。

### 3. Alpha.20 Revision Contract

#### 3.1 状态流

```text
Revision Plan: proposed
-> approval-pending
-> approved / rejected / changes-requested
-> ready
-> waiting-for-tool / waiting-for-result
-> review-pending
-> passed / review-required / blocked
-> resolved only after passing review and supersession
```

#### 3.2 安全门槛

Revision Tool Execution 必须满足：

```text
Task is completed or recoverably waiting
Revision Approval == approved
Revision Job.executable == true
Contract QA == passed
Configured Tool supports image-editing
Configured Tool supports protected-region-editing
Source Reference is inside Project
Source file exists
actual source SHA-256 == registered source SHA-256
```

#### 3.3 Source 与 Replacement

- Source Artifact 不允许 In-place Overwrite；
- Replacement 注册后保存 `revision_id`、`revision_job_id` 和 `source_artifact_id`；
- Source 保存 `replacement_candidates`；
- Metadata Recheck 不触发 Supersession；
- Semantic Review Passed 才执行 Supersession；
- Supersession 保留 Source File、Review 和完整 Provenance。

### 4. 后续迭代

#### alpha.21：Host / Tool Discovery 与 Connection Workflow

- Registered / Available / Installable Tool 状态；
- Host Capability Discovery Protocol；
- Install / Connect Request Schema；
- Permission、Data Scope、External Call、Cost 与 Credential Disclosure；
- Health Check Retry；
- Plugin Contract Test Runner。

#### alpha.22：Gated Export Agent

- Export Agent 消费 Active Artifact、Contract QA 和 Visual Review Gate；
- 将 Approved Production Asset Materialize 到 Project Truth；
- Native Engine Import Integration；
- Export Manifest、Rollback 和 Audit。

#### alpha.23：Git Change Management 与 Host API

- Stable Host Result Protocol；
- Authenticated Actor Identity；
- Git Change Set、Branch、Commit、Rollback；
- Pause、Cancel、Streaming 和 Result Summary。

### 5. 开发决策门槛

任何新 Feature 开始前必须回答：

1. 它是否直接服务 GUIF 的产品定义？
2. 它是否属于 Target Architecture 中明确的职责？
3. 它是否填补 Current State 中的真实缺口？
4. 它是否推进可验证的 End-to-end Loop，而不只是增加 Interface？
5. 是否定义 Test、Failure Behavior、Persistence、Recovery 和 Acceptance Criteria？
6. 是否同步更新中英文 README 和本文件？

### 6. 主要风险与待验证假设

- ChatGPT Host 如何自动完成 Handoff Callback，而不依赖用户手工 CLI；
- Semantic Inspector 应作为 ChatGPT Tool、独立 Tool 还是 Human Review；
- Revision Mask、Target Region 和 Preserve Region 应如何形成 Provider-neutral Contract；
- Tool Manifest 是否需要签名、权限模型和可信来源；
- Tool Resolver 何时应考虑 Cost、Latency、Privacy 和 Quality；
- Task Waiting State 是否需要 Lease、Timeout 和 Optimistic Lock；
- External Result Submission 如何认证 Host Identity；
- Upstream Contract 变化后，Approval、Handoff、Artifact 和 Revision 是否应自动失效；
- 如何防止 Framework 继续增加 Contract，却没有完成真实产品侧自动调度。

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
- `alpha.18`：Visual Artifact Inspection、Revision Plan、Supersession。
- `alpha.19`：Configurable Host / Tool、ChatGPT Bridge、Layered Resolution、Waiting State、External Submission 和 Fail-closed Policy。
- `alpha.20`：Revision Job Construction、Independent Revision Approval、Immutable Source Binding、Configured Editing Tool Execution、Automatic Metadata Recheck 与 Review-gated Supersession。

---

## English Version

### 0. Purpose

This file is GUIF's living product definition, verified capability review, risk register, and iteration baseline. It must change in the same release whenever product scope, architecture, capability status, compatibility, priorities, or acceptance criteria change.

### 1. Expected product

GUIF is an executable game UI production framework with a natural-language interface, configurable Hosts, configurable Tools, Git-backed Project truth, inspectable execution, and recoverable state.

ChatGPT is the default Host and `chatgpt-image` is the default generation and editing Tool. They are replaceable defaults, not Core dependencies.

```text
User
-> ChatGPT Host by default
-> GUIF Runtime
-> deterministic production Agents
-> initial Approval
-> configured Tool execution
-> Artifact Registry
-> Visual Review
-> Revision Plan
-> versioned edit Job
-> independent Revision Approval
-> editing Tool
-> replacement Artifact
-> re-review
-> gated supersession
-> gated Export
```

Core principles:

- configurable Hosts and Tools;
- ChatGPT-first default experience;
- production fail-closed behavior;
- review before mutation or execution;
- separate approval for later revisions;
- immutable source binding;
- explicit external result submission;
- deterministic contracts and immutable provenance;
- no false visual verification;
- no supersession before a passing replacement review.

### 2. Verified state at alpha.20

GUIF can convert a persisted Revision Plan into a versioned edit Job. The Job retains the original Prompt contract, adds finding-derived objectives and preservation constraints, binds the source Artifact as an immutable reference, and creates an independent Revision Approval gate.

Approved Revision Jobs route through the same configurable Tool system introduced in alpha.19. The default path creates a `chatgpt-image` editing handoff. Source file identity is verified against the registered SHA-256 before invocation; a missing or modified source fails closed.

A submitted replacement is linked to the Revision Plan, Job, Review, and source Artifact. GUIF automatically runs eligibility, integrity, and image metadata review. The source remains active until the replacement receives a passing semantic visual review. A pass marks the source stale and records bidirectional supersession provenance.

### 3. Remaining gaps

- automatic ChatGPT Product callback wiring;
- a default semantic visual inspector;
- authenticated Host and Approval identities;
- install / connect / credential workflow;
- dynamic Tool plugin loading and distribution;
- mask and multi-source Revision contracts;
- gated production Export Agent;
- Git change management.

### 4. Next phases

1. `alpha.21`: Host / Tool discovery, registered / available / installable states, connection requests, permission and cost disclosure, credential workflow, health retry, and plugin contract tests.
2. `alpha.22`: Gated Export Agent and native Engine materialization.
3. `alpha.23`: Authenticated Host API and Git change management.

### 5. Iteration gate

A Feature must serve the product definition, belong to the target architecture, close a verified gap, advance an end-to-end loop, define tests and recovery behavior, and update both READMEs plus this specification.

### 6. Main risks

The principal unresolved questions concern automatic Host callbacks, semantic inspection ownership, provider-neutral masks and target regions, Tool trust and signing, cost/privacy-aware routing, waiting-state concurrency, Host authentication, stale Contract invalidation, and avoiding interface growth without product-side automation.

### 7. Iteration history

- `alpha.9`–`alpha.18`: Runtime, persistence, production Agents, Approval, Provider execution, Artifact Registry, Visual Review, Revision Planning, and Supersession.
- `alpha.19`: configurable Hosts and Tools, ChatGPT defaults, layered resolution, waiting states, external Handoffs, result submission, Adapter scaffolding, and fail-closed routing.
- `alpha.20`: versioned Revision Jobs, independent Revision Approval, immutable source hash binding, configurable editing execution, automatic metadata recheck, and review-gated supersession.
