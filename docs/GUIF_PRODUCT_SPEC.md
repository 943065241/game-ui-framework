# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.19`  
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
       -> Revision Plan / Revision Execution
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
- **Fail Closed**：生产任务缺少 Tool 时必须暂停，不得静默回退到 Simulation。
- **No False Verification**：Simulation、Metadata Check 和 Visual Semantic Review 必须明确区分。
- **Immutable Provenance**：Revision 不覆盖原 Artifact，旧结果通过 Supersession 关联保留。

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
       -> Approval Gate
       -> Tool Resolver
            -> Tool Registry
            -> Tool Manifest
            -> Tool Health Check
            -> Direct Tool Adapter
            -> External Callback Tool Adapter
       -> Tool Handoff / Result Submission
       -> Artifact Registry
       -> Visual Review Service
       -> Revision Planner / Executor
       -> Export Gate
       -> Task Store / Git Change Management
```

职责边界：

- **Host**：理解对话、声明当前环境能力、处理用户确认、选择 Tool 并提交 External Result。
- **Runtime**：执行 Workflow、维护 Task Lifecycle、协调 Approval、Tool Resolution、Execution 和 Artifact State Transition。
- **Tool Manifest**：声明 ID、Version、Capability、Execution Mode、Environment、Credential、Host Support 和 I/O Contract。
- **Tool Resolver**：按 Explicit、Task、Project、Workspace、Framework 顺序解析 Tool。
- **Tool Adapter**：将 Tool Request 转换为 Direct Result 或 External Handoff。
- **Artifact Registry**：保存 Artifact File、Hash、MIME、Dimension、Tool Metadata、Approval Snapshot 和 Provenance。
- **Visual Review Service**：区分 Simulation 与真实图片，执行 Integrity、Metadata 和可选 Semantic Review。
- **Revision Plan**：将 Finding 关联到 Source Job 和 Source Artifact，不覆盖原文件。
- **Export Gate**：只有 Contract QA 与 Active Visual Artifact Review 全部通过时才允许真实 Export。

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
- 为了简化流程而覆盖或删除旧 Artifact 与 Review Provenance。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.19` 仓库代码。

状态定义：

- **可用**：已经能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：目标明确，但仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录、`project.json`、`runs/` 与默认 ChatGPT Execution Config | Migration、Template、Archive、Schema Upgrade |
| Workflow / Pipeline | 基础可用 | Workflow-driven、Project Override、Checkpoint、Resume | Branch、Concurrency、Skip、Cancel、Policy Retry |
| Planner / Director / Theme / Resource / Prompt | 基础可用 | 真实确定性 Agent，生成 Plan、Direction、Theme Contract、Resource Bundle 和 Prompt IR | 更复杂 Page Tree、Interaction Flow、Reference Image Review |
| Semantic Contract QA | 基础可用 | 校验 Prompt、Theme、Resource、Approval、Capability 与执行安全 | Cross-page、Usability 和真实 Visual Semantic QA |
| Persistent Approval | 基础可用 | Approve / Reject / Request Changes、History、Prompt Gate、QA Refresh | Authenticated Identity、Role、Expiry、Contract Hash Invalidation |
| Host Profile | 基础可用 | 默认 `chatgpt`，声明 Generation、Editing、Inspection 与 Git Capability | Host Discovery Protocol、Authenticated Identity、Multiple Active Hosts |
| Tool Manifest | 可用 | ID、Version、Capability、Execution Mode、Environment、Production Policy、Host Support、I/O Contract | Manifest Migration、Signature、Distribution Metadata |
| Tool Registry | 基础可用 | 注册 `chatgpt-image` 与 `dry-run`，列出 Manifest 和 Capability | Dynamic Plugin Loading、Remote Catalog、Dependency Isolation |
| Tool Resolution | 基础可用 | Explicit -> Task -> Project -> Workspace -> Framework，保存 Source、Health、Candidate、Reason、Actions | Fallback Policy、Cost / Latency Policy、Multi-tool Composition |
| ChatGPT Image Bridge | 基础可用 | 默认 External Callback Tool，生成完整 Handoff 并等待 Host Result | ChatGPT Product-side automatic callback wiring、Streaming Progress |
| Missing Tool Recovery | 基础可用 | Task 进入 `waiting-for-tool`，保存 Resolution，配置后执行同一 Job | Install / Connect UI、Credential Workflow、Automated Health Recheck |
| External Result Submission | 可用 | 校验 Handoff Identity，登记真实文件，恢复 Task，刷新 QA | Chunked Upload、Remote URI、Authenticated Submitter |
| Dry-run Tool | 可用 | 确定性非视觉 Receipt；显式选择；不会自动成为 Production Fallback | 仅验证 Contract，不生成 Pixel |
| Task / Task Store | 基础可用 | Task schema v3；Pipeline、Tool Waiting、Handoff、Artifact、Review、Revision 持久化 | Migration Tool、Diff、Replay、Search、Optimistic Lock |
| Artifact Registry | 基础可用 | ID、File、SHA-256、MIME、Dimension、Tool/Provider Metadata、Reference、Approval、QA | Remote Store、Retention、Database、Artifact Signing |
| Visual Review | 基础可用 | Eligibility、Integrity、Metadata、可选 Inspector、Revision Plan、Supersession | 默认 Semantic Inspector、Cross-page Review、Human Review UI |
| Adapter Scaffold | 基础可用 | 生成 `tool.json`、`adapter.py`、Schema、README 与 Test Scaffold | 自动 Contract Test Runner、Packaging、Installation |
| Export | 基础可用 | Generic / Unity / Godot / Unreal Metadata Adapter | Export Agent 仍 Contract-only；未消费最终 Visual Gate |
| Git Change Management | 未开发 | Git 是原则，但 Runtime 不管理 Commit Lifecycle | Change Set、Branch、Commit、Rollback、Approval |

#### 2.1 当前可真实完成的闭环

```text
Project Init
-> 默认 ChatGPT Host / Tool Config
-> Requirement -> Plan / Direction / Theme / Resource / Prompt
-> Contract QA -> Approval
-> Tool Resolution
-> ChatGPT Handoff 或显式 Dry-run
-> External Result Submission
-> Artifact Registration
-> Visual Eligibility / Metadata Review
-> Revision Plan / Artifact Supersession
```

#### 2.2 当前不能自动完成的关键闭环

GUIF 现在可以准备 ChatGPT Handoff 并接收结果，但 GUIF Core 本身无法主动调用 ChatGPT Product 内的图片工具。实际生产仍需要 ChatGPT Host 执行图片生成或修图，并调用 Result Submission API。

Revision Plan 目前不会自动变成新的 Edit Job，也不会自动建立 Revision Approval、执行 Replacement、触发 Re-review 和 Supersession。

### 3. Host 与 Tool 配置原则

#### 3.1 配置优先级

```text
Explicit Tool
-> Task Override
-> Project Config
-> Workspace Config
-> Framework Default
```

默认：

```json
{
  "mode": "production",
  "default_host": "chatgpt",
  "tools": {
    "image-generation": {"primary": "chatgpt-image", "fallback": []},
    "image-editing": {"primary": "chatgpt-image", "fallback": []}
  }
}
```

#### 3.2 缺少 Tool 时

```text
required
-> resolving
-> waiting-for-tool
-> user binds / connects / implements Tool
-> health check
-> execute same persisted Job
```

不得执行：

```text
missing Tool
-> silent dry-run fallback
-> return JSON receipt as if image completed
```

#### 3.3 External Callback

```text
GUIF Tool Request
-> ChatGPT Host Handoff
-> Host calls image generation / editing
-> Host submits real file
-> GUIF registers Artifact and refreshes QA
```

#### 3.4 `dry-run`

`dry-run` 只能在 Development / CI，或用户明确选择时使用。它不是生产默认 Tool，也不是 Missing Tool Fallback。

### 4. 后续迭代

#### alpha.20：Revision Job Construction + Controlled Revision Execution

- 将 Revision Plan 转换为版本化 Edit Job；
- 将 Source Artifact 绑定为 Immutable Reference；
- 建立独立 Revision Approval Gate；
- 使用配置的 `image-editing` Tool；
- Replacement Artifact 自动关联 Source Artifact；
- 自动触发 Re-review；
- 只有 Replacement Review 通过后才能 Supersede Source。

#### alpha.21：Host / Tool Discovery 与 Connection Workflow

- Host Capability Discovery Protocol；
- Available / Registered / Installable Tool 状态；
- Install / Connect Request Schema；
- Permission、Data Scope、External Call、Cost 与 Credential Disclosure；
- Health Check Retry；
- Plugin Contract Test Runner。

#### alpha.22：Gated Export Agent

- Export Agent 消费 Active Artifact、Contract QA 和 Visual Review Gate；
- 将 approved Production Asset Materialize 到 Project Truth；
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
5. 是否定义了 Test、Failure Behavior、Persistence、Recovery 和 Acceptance Criteria？
6. 是否同步更新中英文 README 和本文件？

### 6. 主要风险与待验证假设

- ChatGPT Host 如何自动完成 Handoff Callback，而不依赖用户手工 CLI；
- Tool Manifest 是否需要签名、权限模型和可信来源；
- Tool Resolver 何时应考虑 Cost、Latency、Privacy 和 Quality；
- Task Waiting State 是否需要 Lease、Timeout 和 Optimistic Lock；
- External Result Submission 如何认证 Host Identity；
- Upstream Contract 变化后，Approval、Handoff 和 Artifact 是否应自动失效；
- Tool 安装与 Credential 应由 GUIF、Host 还是 Plugin Manager 管理；
- 如何防止 Framework 继续增加 Contract，却没有完成真正的图片生产闭环。

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
- `alpha.18`：Visual Artifact Inspection Contract、Revision Plan、Supersession。
- `alpha.19`：Configurable Host / Tool、ChatGPT Default Bridge、Layered Resolution、Waiting State、External Result Submission、Adapter Scaffold 和 Production Fail-closed Policy。

---

## English Version

### 0. Purpose

This file is GUIF's living product definition, verified capability review, risk register, and iteration baseline. It must change in the same release whenever product scope, architecture, capability status, compatibility, priorities, or acceptance criteria change.

### 1. Expected product

GUIF is an executable game UI production framework with a natural-language interface, configurable Hosts, configurable Tools, Git-backed Project truth, inspectable execution, and recoverable state.

The default path uses ChatGPT as the Host and `chatgpt-image` as the image-generation and image-editing Tool. These are replaceable defaults, not Core dependencies.

```text
User
-> ChatGPT Host by default
-> GUIF Runtime
-> deterministic production Agents
-> Approval
-> Tool Resolver
-> external Handoff or direct Tool execution
-> Artifact Registry
-> Visual Review / Revision
-> gated Export
```

Core principles:

- Host and Tool configuration;
- ChatGPT-first default experience;
- production fail-closed behavior;
- no implicit Dry-run fallback;
- review before mutation or execution;
- explicit external result submission;
- deterministic contracts and immutable provenance;
- no false visual verification.

### 2. Verified state at alpha.19

GUIF now provides Tool Manifests, a Tool Registry, layered Tool Resolution, Host capability declarations, Tool health checks, recoverable `waiting-for-tool` and `waiting-for-tool-result` Task states, the default `chatgpt-image` external bridge, explicit `dry-run`, external file submission, Tool Handoff persistence, and Adapter scaffolding.

The resolver uses this precedence:

```text
explicit -> Task -> Project -> Workspace -> Framework default
```

When a configured Tool is missing, unhealthy, unsupported by the Host, or unable to bind required References, GUIF persists the reason and recovery actions and stops. It does not generate a simulated receipt automatically.

The ChatGPT bridge prepares a structured Handoff. ChatGPT performs generation or editing outside GUIF Core, then submits the real file. GUIF registers the Artifact, restores the Task, refreshes QA, and retains all execution and Approval evidence.

### 3. Remaining gaps

- automatic ChatGPT Product callback wiring;
- authenticated Host identity;
- install / connect / credential workflow;
- dynamic Tool plugin loading and distribution;
- Revision Plan to Edit Job automation;
- default semantic visual inspector;
- gated production Export Agent;
- Git change management.

### 4. Next phases

1. `alpha.20`: Revision Job construction, immutable source binding, Revision Approval, configured editing Tool execution, replacement Artifact and automatic re-review.
2. `alpha.21`: Host / Tool discovery, installable states, connection requests, permission and cost disclosure, credential workflow, and plugin contract tests.
3. `alpha.22`: Gated Export Agent and native Engine materialization.
4. `alpha.23`: Authenticated Host API and Git change management.

### 5. Iteration gate

A Feature must serve the product definition, belong to the target architecture, close a verified gap, advance an end-to-end loop, define tests and recovery behavior, and update both READMEs plus this specification.

### 6. Main risks

The main unresolved questions concern automatic Host callback integration, Tool trust and signing, cost/privacy-aware routing, waiting-state concurrency, Host authentication, stale Approval invalidation, credential ownership, and avoiding interface growth without a proven visual production loop.

### 7. Iteration history

- `alpha.9`–`alpha.18`: Runtime, persistence, structured production Agents, Approval, Provider execution, Artifact Registry, Visual Review, Revision Planning, and Supersession.
- `alpha.19`: configurable Hosts and Tools, ChatGPT defaults, layered resolution, recoverable waiting states, external Handoffs, result submission, Adapter scaffolding, and fail-closed production routing.
