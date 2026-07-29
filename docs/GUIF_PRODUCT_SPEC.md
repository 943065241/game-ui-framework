# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.16`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅和后续迭代基线，不是一次性 Roadmap，也不是宣传文案。

发生以下变化时，必须在同一个 Release 或 Pull Request 中同步更新本文件：

- 产品定位、边界或核心原则变化；
- Runtime、Task、Agent、Workflow、Pipeline、Context、Memory、Theme、Resource、Prompt、Approval、QA、Artifact 或 Export 等核心能力变化；
- 某项能力从 Contract / 占位升级为真实可执行能力；
- CLI、Agent Host 接入、Project 目录或数据格式发生兼容性变化；
- 迭代优先级、风险或待验证假设变化。

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
  -> Human / Host 持久化 Approval Decision
  -> Provider Adapter 只执行已批准 Job
  -> Artifact Registration 保存产物和 Provenance
  -> Visual QA 检查并驱动 Revision Loop
  -> Export Agent 交付 Engine-ready Output
  -> 保存 Task、Output、Decision、Report 和 Git Change
```

CLI 保留用于开发、调试、自动化和 CI，但不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户描述目标，Framework 负责拆解、约束和执行。
- **长期 Project Knowledge**：Theme、Decision、Lesson、Mistake 和 Best Practice 由 Project File 与 Git 追踪。
- **可执行而非 Prompt Collection**：GUIF 必须产生结构化 Task、Plan、Review、Contract、Prompt IR、Approval、QA Report、Artifact 和可验证结果。
- **Model Agnostic**：Runtime、Prompt IR 和 QA Contract 不直接依赖单一模型或 Provider。
- **Project Isolation**：Framework Code 与具体游戏 Project 分离。
- **Deterministic Production**：Naming、Dimension、Alpha、Validation、Export 和 Engine Adaptation 尽可能可重复。
- **可审计、可恢复**：每个 Run 必须说明读取了什么、选择了什么、执行到哪里、产生了什么、为什么失败以及如何继续。
- **Review Before Write / Execute**：推导结果未经批准，不得成为 Project Truth，也不得自动提交给 Provider 执行。
- **Explicit Approval**：Approval 必须有 ID、Actor、Decision、时间和可追溯 History，不能靠隐式推断。
- **No False Verification**：没有检查视觉 Artifact 时，不得声称完成视觉 QA。

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
       -> Approval Service
       -> Provider / Tool Adapter
       -> Artifact Registry
       -> Visual QA Adapter / Agent
       -> Export Agent
       -> Outputs + Reports + Memory + Git Changes
```

职责边界：

- **Agent Host**：理解对话、确认用户意图、提供 Actor Identity、处理 Approval，并解释结果。
- **Runtime**：加载 Context、执行相关性选择、解析 Workflow、创建或恢复 Task、调度 Agent、保存 Checkpoint 和处理失败；不包含具体 Provider 逻辑。
- **Context Loader**：创建完整、可持久化的 Project Context Snapshot。
- **Context Retrieval**：选择相关记录并保留 Score、Matched Term、Budget 和 Provenance。
- **Workflow**：声明人类可读 Step 与可执行 Agent Order。
- **Pipeline**：Workflow 在一次 Run 中的解析结果，负责执行与恢复位置。
- **Task Store**：持久化 Task、Context、Event、Output、Approval 和 Error。
- **Agent**：完成单一职责；Agent 不直接调用其他 Agent。
- **Prompt IR**：Provider-independent 的 Generation / Editing Contract，不是任何具体 API Payload。
- **Approval Service**：持久化 Approve、Reject 与 Request Changes，并受控刷新 Prompt 和 QA Gate；不写 Project、不调用 Provider。
- **Semantic QA Report**：验证上游 Contract、一致性、Approval 与 Execution Gate；没有视觉 Artifact 时只做 Contract QA。
- **Provider Adapter**：将已批准 Prompt Job 转换为具体 Tool / Model 调用。
- **Artifact Registry**：登记真实产物、文件引用、Provider Metadata、Input / Output Contract 和 Provenance。
- **Export Gate**：只有 Contract、Artifact、QA 与 Approval 全部满足时才允许 Export。
- **Git**：长期事实来源、变更记录和协作边界。

#### 1.5 非目标

GUIF 不计划：

- 替代 Photoshop、Figma、Unity、Godot 或 Unreal；
- 管理完整游戏逻辑、Server、数值或关卡代码；
- 训练基础模型；
- 成为任意行业的通用 Agent Framework；
- 将全部 AI 与 Tool Logic 塞进 Runtime；
- 用不可追踪的 Chat Memory 替代 Project File 与 Git；
- 在没有明确 Review / Approval 的情况下把推导结果写入 Project 或提交给 Provider；
- 把 Approval 等同于 Theme / Resource Materialization；
- 在没有实际检查 Artifact 时宣称视觉质量、构图或可用性已经通过。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.16` 仓库代码。

状态定义：

- **可用**：能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录、`project.json` 和 `runs/` | Migration、Template、Archive、Schema Upgrade |
| Workflow | 基础可用 | Schema v2 声明 `steps` 与 `agents`；Built-in / Project Override；v1 兼容 | Condition、Loop、Error Policy、Approval Gate Declaration、Migration |
| Pipeline | 基础可用 | 由 Workflow 构建；保存 Source、Manager、Step 和 Agent Order；支持 Checkpoint / Resume | Branch、Concurrency、Skip、Cancel、Policy Retry |
| Runtime | 基础可用 | Context Load、Relevance Selection、Workflow Resolve、Task Create / Resume、Failure Persistence、Approval API | Capability Discovery、Concurrency、Cancel、Atomic Multi-writer Control |
| Task / Task Store | 基础可用 | Schema v2；Lifecycle、Event、Output、Error；Run Directory；`approvals.json` | Strict Agent I/O Schema、Migration、Diff、Replay、Search、Locking |
| Context Retrieval | 基础可用 | Requirement + Active Theme 排序；英文 Token、中文 n-gram、Budget、Score、Matched Term | Embedding Retrieval、Index、History / Artifact Retrieval |
| Structured Planner | 基础可用 | Page、Dimension、Orientation、Engine、Theme、Reuse、Missing Resource、QA、Risk、Open Question | Typed Subtask、Component Tree、Interaction Flow、LLM Adapter |
| Structured Director | 基础可用 | Composition Zone、Focal Order、Memory Constraint、Reuse Decision、Conflict、Approval Point、Handoff | Reference Image Review、Cross-page Comparison、Complex Layout Reasoning |
| Structured Theme Agent | 基础可用 | Active Theme 解析；Preset 推导；Memory Constraint；Conflict；状态管理 | Visual Token、Inheritance、Version、Reference、Materialization API |
| Structured Resource Agent | 基础可用 | Existing Reuse、Manifest Candidate、Dimension Provenance、Engine Hint、Conflict、Approval Point | Variant、Dependency、Atlas、Nine-slice、Materialization API |
| Structured Prompt Agent | 基础可用 | Provider-independent Prompt IR；Effect Image / Asset Job；Instruction；Constraint；Reference；Output Contract；Capability；Approval；Blocker；Provenance | Provider Adapter、Reference File Binding、Capability Negotiation |
| Persistent Approval API | 基础可用 | `get_approvals`、`approve`、`reject`、`request_changes`；Actor / Comment / Timestamp；Latest Record + Append-only History；受控刷新 Prompt 与 QA；CLI | Authenticated Identity、Role Policy、Signature、Optimistic Lock、Approval Expiry、Upstream-change Invalidation |
| Structured Semantic QA | 基础可用 | Prompt Schema、Provenance、Page、Theme、Resource Job、Reference、Execution Gate、Capability、Approval State 检查；Export Gate | 视觉 Artifact Inspection、Cross-page / Usability QA、Revision Execution |
| Theme File Management | 基础可用 | 创建、激活和校验 Theme File | Migration、Inheritance、Version、Conflict Resolution |
| Resource Manifest | 可用 | Dimension、Format、Alpha、Naming、Target Engine、Import Hint | Variant、Atlas、Nine-slice、Dependency Graph |
| Memory | 基础可用 | Markdown Decision、Lesson、Mistake、Best Practice；Runtime 可读取和检索 | Auto Capture、Dedup、Priority、Expiry、Approval State |
| Asset QA | 可用 | 校验真实图片的 Dimension、Format、Alpha 和 Naming | Art Consistency、Layout、Readability、Multi-resolution QA |
| Protected Editing | 可用 | Mask Composition 并验证非目标像素 | 尚未进入 Runtime Revision Loop |
| Provider / Generation | 未开发 | Prompt Job 可在 Approval 后标记 `executable`，但没有任何 Provider 调用 | Provider Adapter、Capability Discovery、Cost / Quota、Retry、Reference Binding |
| Artifact Registry | 未开发 | Task Output 可登记通用对象，但没有正式 Artifact Schema | File Reference、Hash、Provider Metadata、Input / Output Link、Storage Policy |
| Visual Semantic QA | 未开发 | 当前仅 Contract QA；Artifact Review 明确为 `not-run` | Image Inspection Adapter、Theme / Composition / Content / Usability Review |
| Export | 基础可用 | Generic / Unity / Godot / Unreal Adapter Metadata | Export Agent 仍是 Contract；尚未消费真实 Artifact 和 Visual QA Gate |
| Host Integration | 未开发 | README 提供 Runtime 与 Approval 示例 | Stable Result Protocol、Identity、Pause、Streaming、Host Guide |
| Git Change Management | 未开发 | Git 是原则但 Runtime 不管理 Commit Lifecycle | Change Set、Branch / Commit、Rollback、Approval、Audit |

#### 2.1 当前可以真实完成的闭环

```text
Project Init
-> 创建 Theme、Workflow、Memory 和已有 Resource Manifest
-> Requirement 进入 Runtime
-> Context Selection
-> Workflow -> Pipeline
-> Planner -> Director -> Theme -> Resource -> Prompt
-> Semantic Contract QA
-> Task / Context / Event / Output / Approval 持久化
-> Human / Host Approve、Reject 或 Request Changes
-> Prompt Status 与 Job executable 受控刷新
-> Semantic QA 自动重建
```

针对《韭菜派对》中世纪港口商店页，当前可以自动输出并管理：

- Page、Canvas、Orientation、Target Engine；
- Theme、Memory、Composition 与 Resource Reuse；
- Missing Resource Manifest Candidate；
- Provider-independent Effect Image / Production Asset Job；
- Instruction、Negative Constraint、Reference、Output Contract 与 Acceptance Criteria；
- Contract Check、Finding、Revision Request 与 Export Gate；
- Approval Point、Actor、Decision、Comment、Timestamp 和 History；
- `pending / approved / rejected / changes-requested`；
- `review-required / blocked / ready` Prompt 转换；
- 非 `ready` Job 禁止执行。

#### 2.2 当前尚不能完成的关键闭环

```text
“为 LeekParty 制作一个符合现有中世纪港口风格的商店页面，
复用已有金币和按钮，生成缺失资源，检查后导出 Unity。”
```

GUIF 已能完成规划、契约、Contract QA 和 Approval Gate，但仍缺少 Provider Adapter、Artifact Registration、视觉 Semantic QA、Revision Loop、Theme / Resource Materialization 和真实 Export Agent，因此尚不能自动产生视觉 Artifact 并交付完整 Engine-ready Output。

### 3. GUIF 预期待开发的内容

开发顺序以尽快验证真实可用闭环为原则，而不是继续增加空 Interface。

#### Phase 1：可审计、可恢复的 Runtime 基础

已完成：Task Lifecycle、Run Directory、Context / Event / Output / Error、Checkpoint、Load / List / Resume、Workflow / Pipeline 统一、Project Override、Agent Order 安全检查和 Persisted Context Selection。

仍待：Skip、Cancel、Retry Policy、Capability Discovery、Migration、Diff、Replay 和并发写入控制。

#### Phase 2：Planner + Director

已完成第一版结构化 Plan、Composition、Hierarchy、Reuse、Conflict、Approval Point 和 Handoff。

仍待：Typed Subtask、Complex Component Tree、Interaction Flow、Reference Image Review、Cross-page Comparison 与可替换 LLM Adapter。

#### Phase 3：Context 与 Memory Retrieval

已完成确定性相关性选择、英文 Token、中文 n-gram、Budget、Score、Matched Term 和 Persisted Selection。

仍待：Historical Run、Approved Artifact、Embedding Index、Dedup、Source Hash 和 Context Refresh Policy。

#### Phase 4：Theme + Resource Contract

已完成 Active Theme、Preset 推导、Memory Constraint、Resource Manifest Candidate、Dimension Provenance、Engine Hint 和 Review-before-write。

仍待：Materialization API、Visual Token、Theme Inheritance、Variant、Dependency、Atlas、Nine-slice 和 Reference Graph。

#### Phase 5：Prompt IR + Semantic Contract QA

已完成 Prompt IR schema v1、Effect Image / Production Asset Job、Provider Placeholder、Constraint、Reference、Capability、Approval Point、Blocker、Provenance，以及 Contract QA 与 Export Gate。

仍待：Prompt Migration、Reference File Binding、Provider Capability Negotiation 和 Prompt Evaluation。

#### Phase 6：Persistent Approval

alpha.16 已完成第一版：

- `approval_state` 与 `approvals.json`；
- `not-required / pending / approved / rejected / changes-requested`；
- Actor、Comment、Timestamp、Question、Source；
- Latest Record 控制 Gate，History 追加保存；
- Approve、Reject、Request Changes 可覆盖当前 Decision；
- 全部必要 Approval 通过后，Prompt IR 受控变为 `ready`；
- Reject / Request Changes 生成 Approval Blocker；
- 每次 Decision 后重建 Semantic QA；
- Run List 展示 Approval Status；
- Task 保持 `completed`；
- `project_mutated: false` 与 `provider_executed: false`。

仍待：Authenticated Actor、Role / Policy、Digital Signature、Optimistic Lock、Approval Expiry、Upstream Contract Hash 和自动失效规则。

#### Phase 7：Provider Adapter + Artifact Registry

下一迭代目标：只执行已批准且 `executable: true` 的 Prompt Job。

需要包含：

- Provider / Tool Capability Discovery；
- Prompt IR -> Provider Payload Adapter；
- Provider-independent Execution Request / Result Schema；
- Reference File Binding；
- Artifact ID、Path / File Reference、Hash、MIME、Dimension；
- Provider、Model、Request ID、Cost / Quota 和 Timing Metadata；
- Prompt Job、Resource Manifest、Artifact 双向引用；
- Retry、Alternative、Failure Persistence；
- Approval、QA 和 Capability Gate 强制检查；
- 默认无 Provider 时提供 Deterministic Dry-run Adapter。

**验收标准**：Provider Adapter 无法执行未批准 Job；成功执行后生成可持久化 Artifact Record；失败不会丢失 Task、Approval 或 Provider Error。

#### Phase 8：Visual Semantic QA + Revision Loop

- Image / UI Inspection Adapter；
- Theme、Composition、Content、Readability 和 Usability；
- Resource Output Contract Compliance；
- Cross-page Consistency；
- QA Finding -> Revision Task -> Recheck；
- 不支持视觉检查时继续明确 `not-run`。

#### Phase 9：Production Export、Host 与 Git Integration

- Real Export Agent 消费 Artifact 与 QA Gate；
- Native Engine Import；
- Stable Host Result Protocol、Identity、Pause 和 Streaming；
- Git Change Set、Commit、Rollback 和 Audit；
- End-to-end Acceptance Test。

### 4. 开发决策门槛

任何新 Feature 开始前必须回答：

1. 是否直接服务 GUIF 产品定义？
2. 是否属于 Target Architecture 中明确职责？
3. 是否填补 Current State 中真实缺口？
4. 是否推进一个可验证 End-to-end Loop，而不是增加占位 Contract？
5. 是否定义 Test、Failure Behavior、Persistence、Approval 和 Acceptance Criteria？
6. 是否避免未经批准写 Project 或调用 Provider？
7. 是否同步更新中英文 README 和本文件？

### 5. 主要风险与待验证假设

- Rule-based Planner 是否能长期保持可维护；
- Mutable Task 是否需要 Typed Subtask；
- Approval ID 是否需要 Namespace 和 Version；
- Actor 字符串在没有 Host Identity Contract 时是否足够可信；
- Upstream Plan / Theme / Resource / Prompt 变化后，旧 Approval 应如何自动失效；
- 多个 Host 同时决策时如何防止 Lost Update；
- Group Approval 是否足以代表每个 Resource Candidate 的具体决定；
- `ready` 是否只代表允许 Provider 准备，还是代表可以立即计费执行；
- Provider Adapter 应在 Runtime 内还是 Plugin Boundary；
- Artifact Store 何时需要 Database / Object Storage；
- 如何避免大量 Interface 继续增长，却没有视觉 Artifact 闭环。

### 6. 迭代记录

- `alpha.9`：Runtime、Task、Agent Registry、Pipeline Contract 和 Context Loading。
- `alpha.10`：Task schema v2、Persistent Run Store、Checkpoint、Failure、Load / List / Resume。
- `alpha.11`：Workflow-driven Pipeline 和第一个 Structured Planner。
- `alpha.12`：Relevance Context Selection 和 Structured Director。
- `alpha.13`：Structured Theme / Resource Agent 与 Review-before-write。
- `alpha.14`：Model-neutral Prompt IR。
- `alpha.15`：Semantic Contract QA、Finding、Revision Request、Artifact Review State 和 Export Gate。
- `alpha.16`：Persistent Approval API、`approvals.json`、Actor / Decision / History、受控 Prompt Job Gate、QA 自动刷新和 Approval CLI。

---

## English Version

### 0. Purpose and maintenance

This file is GUIF's living product definition, verified capability review, and iteration baseline. It must be updated with every change to product scope, architecture, core capability status, compatibility, priority, risk, or open assumptions.

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
-> persistent human Approval
-> Provider execution
-> Artifact registration
-> Visual QA and revision
-> Engine-ready Export
```

Core principles are model independence, Project isolation, deterministic contracts, inspectable and recoverable Runs, explicit Approval, review before write or execute, and no false visual verification.

### 2. Verified state at alpha.16

GUIF can execute deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents. It persists Task Runs, Context, Outputs, errors, and Approval state.

The new Approval API supports `approve`, `reject`, and `request_changes` through Runtime and CLI. Each decision stores the Approval ID, actor, optional comment, timestamp, source, and question. The latest decision controls the current gate while history remains append-only.

Unresolved approvals keep Prompt IR in `review-required`. Rejection or change requests make it `blocked`. When every required Approval is approved and no other blocker exists, Prompt IR becomes `ready` and its jobs become executable. Semantic QA is rebuilt after every decision. Approval does not change Project files, call a Provider, or change the completed Task lifecycle.

The remaining product gap is now concrete: GUIF can prepare and approve executable jobs, but it cannot yet call a Provider, register a real Artifact, visually inspect it, revise it, or perform a real gated Export.

### 3. Expected development

1. Provider Adapter and capability discovery.
2. Artifact Registry with file identity, hash, metadata, and provenance.
3. Visual Semantic QA and revision loops.
4. Real Export Agent consuming Artifact and QA gates.
5. Stable Host identity, result, pause, streaming, and Git-change contracts.

The immediate acceptance target is that an unapproved Prompt job can never execute, while an approved job can produce a persisted Artifact Record through a deterministic dry-run or real Provider Adapter without losing approval or failure history.

### 4. Main risks

Important unresolved questions include authenticated actor identity, approval versioning and expiry, invalidation after upstream contract changes, concurrent decisions, group approval semantics, Provider boundary ownership, Artifact storage, and preventing interface growth without a real visual production loop.

### 5. Iteration history

- `alpha.9`: Runtime contracts and Context loading.
- `alpha.10`: persistent Runs and resume.
- `alpha.11`: Workflow-driven Pipelines and Structured Planner.
- `alpha.12`: Context retrieval and Structured Director.
- `alpha.13`: Structured Theme and Resource contracts.
- `alpha.14`: model-neutral Prompt IR.
- `alpha.15`: Semantic Contract QA and Export Gate.
- `alpha.16`: persistent Approval decisions, controlled Prompt execution state, QA refresh, Approval CLI, and `approvals.json`.
