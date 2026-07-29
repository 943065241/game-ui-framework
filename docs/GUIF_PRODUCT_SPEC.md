# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.17`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅、风险清单和后续迭代基线，不是一次性 Roadmap 或宣传文案。

发生以下变化时，必须在同一个 Release 或 Pull Request 中同步更新本文件：

- 产品定位、边界或核心原则变化；
- Runtime、Task、Agent、Workflow、Pipeline、Context、Memory、Theme、Resource、Prompt、Approval、Provider、Artifact、QA 或 Export 等核心能力变化；
- 某项能力从 Contract / 占位升级为真实可执行能力；
- CLI、Agent Host 接入方式、Project 目录或数据格式发生兼容性变化；
- 迭代优先级、已知风险或待验证假设变化。

一次 Release 只有在 Feature、Test、CI、中英文 README、Version Metadata 和本文件一致时才算完成。

### 1. GUIF 的预期

#### 1.1 一句话定义

GUIF 是一个以自然语言为主要入口、由 ChatGPT 或其他 Agent Host 调度、以 Git 与 Project File 作为长期事实来源、面向游戏 UI 生产全过程的可执行 AI 工作框架。

#### 1.2 预期用户体验

```text
用户：为《韭菜派对》制作中世纪港口商店页面，
复用已有金币和按钮，检查后导出 Unity。

ChatGPT / Agent Host
  -> 选择 Project
  -> 调用 GUIF Runtime
  -> 加载完整 Project Context Snapshot
  -> 选择相关 Memory、Resource 和 Workflow
  -> Planner 生成 Production Plan
  -> Director 生成 Art Direction Review
  -> Theme Agent 生成 Resolved Theme Contract
  -> Resource Agent 生成 Resource Contract Bundle
  -> Prompt Agent 生成 Model-neutral Prompt IR
  -> Semantic QA 检查 Contract 与执行安全
  -> Human / Host 审批 Approval Point
  -> Provider Adapter 执行已批准 Job
  -> Artifact Registry 保存产物与 Provenance
  -> Visual QA 检查真实视觉结果
  -> Revision Loop 修订并复检
  -> Export Agent 交付 Engine-ready Output
  -> 保存 Task、Output、Decision、Report、Artifact 和 Git Change
```

CLI 用于开发、调试、自动化和 CI，不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户表达目标，Framework 负责拆解、约束和执行。
- **长期 Project Knowledge**：Theme、Decision、Lesson、Mistake 和 Best Practice 由 Project File 与 Git 追踪。
- **可执行而非 Prompt Collection**：GUIF 必须产生 Task、Plan、Review、Contract、Prompt IR、Approval、Execution、Artifact 和 QA Report。
- **Model / Provider Agnostic**：Runtime 和 Prompt IR 不直接依赖单一 Provider。
- **Project Isolation**：Framework Code 与具体游戏 Project 分离。
- **Deterministic Production**：Naming、Dimension、Alpha、Validation、Hash、Export 和 Engine Adaptation 尽可能可重复。
- **可审计、可恢复**：Run 必须说明读取了什么、选择了什么、执行了什么、产生了什么、为什么失败，以及如何继续。
- **Review Before Write / Execute**：推导结果未经批准，不得成为 Project Truth，也不得自动提交给 Provider。
- **Capability Before Invocation**：Provider 调用前必须验证 Capability 与 Reference Binding。
- **No False Verification**：没有检查视觉 Artifact 时，不得声称视觉质量已经通过。

#### 1.4 目标架构

```text
User
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> Context Loader
       -> Context Retrieval
       -> Workflow Resolver
       -> Pipeline
       -> Task Store
       -> Agent Registry
            -> Planner Agent
            -> Director Agent
            -> Theme Agent
            -> Resource Agent
            -> Prompt Agent
            -> Semantic QA Agent
       -> Approval Gate
       -> Provider Registry
            -> Dry-run Provider
            -> future Image / Editing / Figma Provider
       -> Artifact Registry
       -> Visual QA Adapter / Agent
       -> Revision Loop
       -> Export Agent
       -> Outputs + Reports + Memory + Git Changes
```

职责边界：

- **Agent Host**：理解对话、确认用户意图、提供 Actor Identity、处理 Approval 并解释结果。
- **Runtime**：加载 Context、解析 Workflow、创建或恢复 Task、调度 Agent、保存 Checkpoint，并执行 Approval / Provider / Artifact 状态转换。
- **Workflow**：声明人类可读 Step 与可执行 Agent Order。
- **Pipeline**：Workflow 在一次 Run 中的解析结果，负责执行顺序与恢复位置。
- **Task Store**：持久化 Task、Context、Event、Output、Approval、Execution、Artifact 和 Error。
- **Agent**：完成单一职责；Agent 不直接调用其他 Agent。
- **Prompt IR**：Provider-independent Generation / Editing Contract，不是具体 API Payload。
- **Approval Gate**：控制 Prompt IR 与 Job 在 `review-required`、`blocked`、`ready` 之间转换。
- **Provider Adapter**：接收 `ExecutionRequest`，返回 `ExecutionResult`，不得绕过 Approval、QA、Capability 或 Reference Gate。
- **Artifact Registry**：保存 Artifact Identity、File、Hash、Metadata、Reference、Approval Snapshot 和 Provenance。
- **Semantic QA**：验证 Contract、一致性和执行安全；没有视觉检查能力时必须保持 `not-run`。
- **Export Gate**：只有 Contract、Approval、Artifact 和 Visual QA 全部满足时才允许真实 Export。
- **Git**：长期事实来源、变更记录和协作边界。

#### 1.5 非目标

GUIF 不计划：

- 替代 Photoshop、Figma、Unity、Godot 或 Unreal；
- 管理完整游戏逻辑、Server、数值或关卡代码；
- 训练基础模型；
- 成为任意行业的通用 Agent Framework；
- 将全部 AI 与 Tool Logic 塞进 Runtime；
- 用不可追踪的 Chat Memory 替代 Project File 与 Git；
- 在没有明确 Approval 的情况下写 Project 或调用 Provider；
- 把 Dry-run Receipt 描述为真实图片；
- 在没有实际检查 Artifact 时宣称视觉质量、构图或可用性通过。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.17` 仓库代码。

状态定义：

- **可用**：能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录、`project.json` 和 `runs/` | Migration、Template、Archive、Schema Upgrade |
| Workflow | 基础可用 | Schema v2 声明 `steps` 与 `agents`；Built-in / Project Override；v1 兼容 | Condition、Loop、Policy、Migration |
| Pipeline | 基础可用 | Workflow-driven；保存 Source、Step、Agent Order；Checkpoint / Resume | Branch、Concurrency、Skip、Cancel、Policy Retry |
| Runtime | 基础可用 | Context、Workflow、Task、Approval、Provider Execution 和 Artifact Registration | Transaction、Concurrency、Cancel、Capability Negotiation |
| Task / Task Store | 基础可用 | Lifecycle、Event、Output、Error、Approval、Execution 与 Artifact Registry | Strict I/O Schema、Migration、Diff、Replay、Search |
| Context Loader / Retrieval | 基础可用 | Project Config、Theme、Workflow、Resource、Markdown Memory；英文 Token、中文 n-gram、Score、Budget | Embedding、History、Artifact Retrieval、Source Hash |
| Structured Planner | 基础可用 | Page、Canvas、Engine、Theme、Reuse、Missing Resource、QA、Risk、Open Question | Typed Subtask、复杂 Component Tree、Interaction Flow |
| Structured Director | 基础可用 | Composition、Hierarchy、Memory Constraint、Reuse Decision、Conflict、Approval | Reference Image Review、Cross-page Comparison |
| Structured Theme Agent | 基础可用 | Active Theme、Preset 推导、Memory 合并、Conflict、状态 | Token、Inheritance、Version、Materialization |
| Structured Resource Agent | 基础可用 | Reuse、Manifest Candidate、Dimension Provenance、Import Hint、Approval | Variant、Atlas、Nine-slice、Dependency、Materialization |
| Structured Prompt Agent | 基础可用 | Provider-independent Prompt IR、Job、Constraint、Reference、Output Contract、Capability、Approval、Blocker | Provider-specific Translation、Prompt Migration |
| Persistent Approval | 基础可用 | Approve / Reject / Request Changes、Actor、Comment、Timestamp、History、Prompt Gate、QA Refresh | Authenticated Identity、Role Policy、Expiry、Contract Hash Invalidation、Optimistic Lock |
| Provider Adapter Contract | 基础可用 | `ExecutionRequest`、`ExecutionResult`、Provider Registry、Capability Gate、Reference Binding Gate | Real Provider、Credential Handling、Quota、Retry Policy、Streaming |
| Dry-run Provider | 可用 | 确定性 JSON Receipt；无外部调用；`simulation: true`、`visual: false`、`billable: false` | 不生成视觉 Pixel，仅验证 Contract 与执行链 |
| Provider Execution Persistence | 基础可用 | Attempt、Request Snapshot、Status、Error、Timing、Latest by Job；失败不破坏 Task / Approval | Retry Command、Backoff、Cancellation、Idempotency Policy |
| Artifact Registry | 基础可用 | Artifact ID、File、SHA-256、MIME、Dimension、Provider、Reference、Output Contract、Approval Snapshot、QA State | Remote Store、Retention、Version、Stale / Superseded、Database |
| Reference Binding | 基础可用 | 将 Resource Manifest `source` 解析为 Project 内 File，并保存 Hash 与 Size | URI、Remote File、Multiple Reference Roles、Sandbox Transfer |
| Structured Semantic QA | 基础可用 | Prompt、Provenance、Page、Theme、Resource、Reference、Execution Gate、Capability；识别 Artifact Metadata | 尚无视觉 Pixel Inspection、Cross-page / Usability QA |
| Visual Semantic QA | 未开发 | Artifact Review 明确保持 `not-run` | Image Inspection Adapter、Theme / Composition / Content / Readability |
| Revision Loop | 未开发 | 可生成 Blocking Finding，但不会自动创建与执行 Revision | Revision Task、Provider Re-execution、Artifact Supersession |
| Export | 基础可用 | Generic / Unity / Godot / Unreal Adapter Metadata | Export Agent 仍 Contract-only；未消费 Artifact / Visual QA Gate |
| Host Integration | 未开发 | Runtime / CLI API 可调用 | Stable Identity、Result Protocol、Pause、Streaming、Approval UI |
| Git Change Management | 未开发 | Git 是原则，但 Runtime 不管理 Commit Lifecycle | Change Set、Branch / Commit、Rollback、Approval、Audit |

#### 2.1 当前可以真实完成的闭环

```text
Project Init
-> Theme、Workflow、Memory 和 Resource Manifest
-> Requirement 进入 Runtime
-> Context Selection
-> Workflow -> Pipeline
-> Plan
-> Director Review
-> Theme Contract
-> Resource Contract Bundle
-> Prompt IR
-> Contract QA
-> Persistent Approval
-> Provider Capability / Reference Gate
-> Deterministic Dry-run Execution
-> Artifact File + Artifact Record
-> Execution / Artifact / Approval / QA 持久化
```

针对《韭菜派对》中世纪港口商店页，当前可以自动输出并保存：

- Page Type、Canvas、Orientation 和 Target Engine；
- Theme、Composition 和 Memory Constraint；
- Existing Resource Reuse 与 Missing Resource Manifest Candidate；
- Provider-independent Job 与 Output Contract；
- Approval Decision 和 History；
- Capability Requirement 与 Bound Reference Hash；
- Deterministic Dry-run Receipt；
- Artifact ID、File、SHA-256、MIME、Dimension 和 Provenance；
- Contract QA、Artifact Review State 与 Export Gate；
- Provider Failure Attempt 与 Error。

#### 2.2 当前尚不能完成的关键闭环

下面的需求仍不能仅靠 GUIF 自动完成全部生产：

```text
“为 LeekParty 制作符合现有中世纪港口风格的商店页面，
复用已有金币和按钮，生成真实视觉资源，检查后导出 Unity。”
```

GUIF 已能把 Job 准备到可批准、可执行，并能通过 Dry-run 验证 Provider / Artifact Contract，但仍不能调用真实图片 Provider、检查真实视觉 Pixel、自动修订、完成视觉 QA 或通过真实 Export Agent 交付 Engine-ready Output。

### 3. 预期待开发内容

开发顺序以“尽快验证真实视觉闭环”为原则，不继续扩充无产出的占位 Interface。

#### Phase 1～6：已完成的基础

- Runtime、Task、Pipeline、Checkpoint、Resume；
- Workflow-driven Agent Order；
- Planner、Director、Theme、Resource、Prompt、Semantic QA；
- Context Retrieval；
- Persistent Approval 与受控 Prompt Gate。

#### Phase 7：Provider Adapter + Artifact Registry

alpha.17 已完成第一版：

- Provider-independent `ExecutionRequest` / `ExecutionResult`；
- Provider Registry 与 Capability Discovery；
- Dry-run Provider；
- 未批准 Job 拒绝执行；
- Contract QA Gate；
- Reference File Binding；
- Artifact File、ID、Hash、MIME、Dimension 和 Provenance；
- `artifacts.json` 与 `executions.json`；
- Provider Failure Persistence；
- CLI Provider / Execute / Artifact 命令。

仍待：

- Real Provider Adapter；
- Credential / Secret Boundary；
- Quota、Cost、Rate Limit 和 Retry Policy；
- Streaming / Async Job；
- Artifact Supersession 与 Approval Invalidation。

#### Phase 8：Visual Artifact Inspection Contract + Revision Planning

下一迭代目标：区分真实视觉 Artifact 与 Simulation，并在不虚构视觉结论的前提下建立 Visual Review Contract。

需要包含：

- Visual Artifact Eligibility：`visual: true`、支持的 MIME、File 存在、Hash 一致；
- Image Metadata Inspection：Dimension、Format、Alpha 与 Output Contract；
- Model-neutral Visual Review Request；
- Visual Inspection Adapter Capability；
- Dry-run Artifact 自动保持 `not-applicable` 或 `not-run`；
- Finding：Theme、Composition、Content、Readability、Usability、Resource Compliance；
- Revision Plan：关联原 Job、Artifact、Finding 和目标修订；
- Artifact Supersession / Stale 状态；
- 没有 Inspection Adapter 时明确保持 `not-run`。

**验收标准**：Dry-run Receipt 不得被识别为视觉结果；真实图片 Metadata 可以确定性检查；没有视觉 Adapter 时不声称通过；Finding 能生成可追溯 Revision Plan。

#### Phase 9：Real Provider + Revision Execution

- 至少一个真实 Generation / Editing Adapter；
- Credential Boundary 与 Capability Negotiation；
- Artifact Upload / Download；
- Retry、Alternative 和 Revision Execution；
- Protected Editing 进入 Runtime Loop；
- 新 Artifact 替代旧 Artifact，并保留 Provenance。

#### Phase 10：Production Export、Host 与 Git Integration

- Real Export Agent 消费 Artifact、Approval 和 QA Gate；
- Native Engine Import；
- Stable Host Identity、Result、Pause、Streaming 和 Approval UI；
- Git Change Set、Commit、Rollback 和 Audit；
- End-to-end Acceptance Test。

### 4. 开发决策门槛

任何新 Feature 开始前必须回答：

1. 是否直接服务 GUIF 产品定义？
2. 是否属于 Target Architecture 的明确职责？
3. 是否填补 Current State 的真实缺口？
4. 是否推进可验证 End-to-end Loop，而不是增加占位 Contract？
5. 是否定义 Test、Failure Behavior、Persistence、Approval 和 Acceptance Criteria？
6. 是否避免未经批准写 Project 或调用 Provider？
7. 是否避免把 Simulation 或 Metadata Check 描述成视觉验证？
8. 是否同步更新中英文 README 和本文件？

### 5. 主要风险与待验证假设

- Rule-based Planner 是否能长期保持可维护；
- Mutable Task 是否需要 Typed Subtask；
- Approval ID 是否需要 Namespace、Version、Expiry 和 Contract Hash；
- Actor 字符串在没有 Host Identity Contract 时是否足够可信；
- 上游 Contract 变化后，旧 Approval 和 Artifact 如何自动失效；
- 多 Host 同时 Approval / Execute 时如何避免 Lost Update；
- Dry-run Capability 是否应与真实 Provider Capability 分开表达；
- Real Provider Credential 应位于 Runtime、Host 还是 Plugin Boundary；
- Provider Retry 如何保证 Idempotency；
- Artifact ID 应基于 Content、Execution 还是 Version；
- Artifact Store 何时需要 Database / Object Storage；
- 视觉检查应使用规则、模型或混合策略；
- 如何避免 Interface 增长快于真实视觉闭环。

### 6. 迭代记录

- `alpha.9`：Runtime、Task、Agent Registry、Pipeline Contract 和 Context Loading。
- `alpha.10`：Task schema v2、Persistent Run Store、Checkpoint、Failure、Load / List / Resume。
- `alpha.11`：Workflow-driven Pipeline 和 Structured Planner。
- `alpha.12`：Relevance Context Selection 和 Structured Director。
- `alpha.13`：Structured Theme / Resource 与 Review-before-write。
- `alpha.14`：Model-neutral Prompt IR。
- `alpha.15`：Semantic Contract QA、Finding、Revision Request、Artifact Review State 和 Export Gate。
- `alpha.16`：Persistent Approval API、受控 Prompt Job Gate、QA 自动刷新和 Approval CLI。
- `alpha.17`：Provider Adapter Contract、Capability / Reference Gate、Deterministic Dry-run Provider、Provider Attempt Persistence、Artifact Registry、Artifact CLI。

---

## English Version

### 0. Purpose and maintenance

This file is GUIF's living product definition, verified capability review, risk register, and iteration baseline. It must be updated with every change to product scope, architecture, core capability status, compatibility, priorities, risks, or assumptions.

A release is complete only when Feature, Tests, CI, both READMEs, Version Metadata, and this specification agree.

### 1. Expected product

GUIF is an executable AI work framework for end-to-end game UI production. Natural language is the primary interface, ChatGPT or another Agent Host performs conversational orchestration, and Git plus Project files remain the long-term source of truth.

Expected flow:

```text
Requirement
-> Context retrieval
-> Workflow / Pipeline
-> Plan
-> Art-direction review
-> Theme and Resource contracts
-> Model-neutral Prompt IR
-> Semantic Contract QA
-> persistent Approval
-> Provider Adapter execution
-> Artifact registration
-> Visual QA
-> Revision
-> Engine-ready Export
```

Core principles are provider independence, Project isolation, deterministic contracts, inspectable Runs, explicit Approval, capability checks before invocation, review before write or execute, persistent evidence, and no false visual verification.

### 2. Verified state at alpha.17

GUIF can execute deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents. It persists Task Runs, Context, Outputs, errors, Approval state, Provider attempts, and Artifact records.

The Provider contract includes `ExecutionRequest`, `ExecutionResult`, a Provider Registry, capability validation, reference-file binding, and failure persistence. The built-in `dry-run` Provider performs no external call and generates no image pixels. It creates a deterministic JSON receipt marked `simulation: true`, `visual: false`, and `billable: false`.

Runtime refuses Provider execution unless the Task is completed, Prompt IR is ready, the Job is executable, Approval is satisfied, Contract QA passes, required capabilities are available, and Providers that require references receive bound files.

Successful execution writes an Artifact file and a record containing Artifact ID, Job, Provider metadata, relative path, SHA-256, MIME type, dimensions, Output Contract, bound references, Approval snapshot, Prompt provenance, and QA state. Provider failures preserve the completed Task and Approval history while recording the failed attempt.

The remaining product gap is concrete: GUIF can prepare, approve, execute, and register a deterministic simulated Artifact, but it cannot yet produce a real visual result, inspect pixels semantically, run a revision loop, or perform a real gated Export.

### 3. Expected development

1. Visual Artifact eligibility and deterministic image metadata inspection.
2. Model-neutral Visual Review Requests and inspection capability discovery.
3. Structured visual Findings and Revision Plans.
4. At least one real Generation / Editing Provider Adapter.
5. Artifact supersession, retry, and revision execution.
6. Real Export Agent consuming Approval, Artifact, and QA gates.
7. Stable Host identity, streaming, and Git-change contracts.

The immediate alpha.18 acceptance target is that Dry-run receipts can never be mistaken for visual Artifacts, real image metadata can be checked against Output Contracts, unavailable visual inspection remains explicitly `not-run`, and QA Findings can produce a traceable Revision Plan.

### 4. Main risks

Important unresolved questions include authenticated identity, Approval invalidation, concurrent decisions, Provider credential ownership, retry idempotency, capability semantics, Artifact identity and storage, visual-review strategy, and preventing interface growth without proving a real visual production loop.

### 5. Iteration history

- `alpha.9`: Runtime contracts and Context loading.
- `alpha.10`: persistent Runs, checkpoints, failures, and resume.
- `alpha.11`: Workflow-driven Pipelines and Structured Planner.
- `alpha.12`: Context retrieval and Structured Director.
- `alpha.13`: Structured Theme / Resource and review-before-write.
- `alpha.14`: model-neutral Prompt IR.
- `alpha.15`: Semantic Contract QA and Export Gate.
- `alpha.16`: persistent Approval and controlled Prompt execution gate.
- `alpha.17`: Provider Adapter contract, deterministic Dry-run execution, capability and reference gates, Provider attempt persistence, and Artifact Registry.
