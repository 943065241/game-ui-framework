# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.15`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅和后续迭代基线，不是一次性 Roadmap，也不是宣传文案。

发生以下变化时，必须在同一个 Release 或 Pull Request 中同步更新本文件：

- 产品定位、边界或核心原则变化；
- Runtime、Task、Agent、Workflow、Pipeline、Context、Memory、Theme、Resource、Prompt、QA 或 Export 等核心能力变化；
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
  -> Human / Host 审批 Approval Point
  -> Generation / Editing Adapter 产生 Artifact
  -> Visual QA 检查并驱动 Revision Loop
  -> Export Agent 交付 Engine-ready Output
  -> 保存 Task、Output、Decision、Report 和 Git Change
```

CLI 保留用于开发、调试、自动化和 CI，但不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户描述目标，Framework 负责拆解、约束和执行。
- **长期 Project Knowledge**：Theme、Decision、Lesson、Mistake 和 Best Practice 由 Project File 与 Git 追踪。
- **可执行而非 Prompt Collection**：GUIF 必须产生结构化 Task、Plan、Review、Contract、Prompt IR、QA Report、Artifact 和可验证结果。
- **Model Agnostic**：Runtime、Prompt IR 和 QA Contract 不直接依赖单一模型或 Provider。
- **Project Isolation**：Framework Code 与具体游戏 Project 分离。
- **Deterministic Production**：Naming、Dimension、Alpha、Validation、Export 和 Engine Adaptation 尽可能可重复。
- **可审计、可恢复**：每个 Run 必须说明读取了什么、选择了什么、执行到哪里、产生了什么、为什么失败以及如何继续。
- **Review Before Write / Execute**：推导结果未经批准，不得成为 Project Truth，也不得自动提交给 Provider 执行。
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
            -> Generation / Editing Adapter
            -> Visual QA Adapter / Agent
            -> Export Agent
       -> Outputs + Reports + Memory + Git Changes
```

职责边界：

- **Agent Host**：理解对话、确认用户意图、处理 Approval，并解释结果。
- **Runtime**：加载 Context、执行相关性选择、解析 Workflow、创建或恢复 Task、调度 Agent、保存 Checkpoint 和处理失败；不包含具体 Provider 逻辑。
- **Context Loader**：创建完整、可持久化的 Project Context Snapshot。
- **Context Retrieval**：选择相关记录并保留 Score、Matched Term、Budget 和 Provenance。
- **Workflow**：声明人类可读 Step 与可执行 Agent Order。
- **Pipeline**：Workflow 在一次 Run 中的解析结果，负责执行与恢复位置。
- **Task Store**：持久化 Task、Context、Event、Output 和 Error。
- **Agent**：完成单一职责；Agent 不直接调用其他 Agent。
- **Prompt IR**：Provider-independent 的 Generation / Editing Contract，不是任何具体 API Payload。
- **Semantic QA Report**：验证上游 Contract、一致性、Approval 与 Execution Gate；没有视觉 Artifact 时只做 Contract QA。
- **Provider Adapter**：将已批准 Prompt IR 转换为具体 Tool / Model 调用，并登记 Artifact。
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
- 在没有实际检查 Artifact 时宣称视觉质量、构图或可用性已经通过。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.15` 仓库代码。

状态定义：

- **可用**：能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录、`project.json` 和 `runs/` | Migration、Template、Archive、Schema Upgrade |
| Workflow | 基础可用 | Schema v2 声明 `steps` 与 `agents`；Built-in / Project Override；v1 兼容 | Condition、Loop、Error Policy、Approval Gate、Migration |
| Pipeline | 基础可用 | 由 Workflow 构建；保存 Source、Manager、Step 和 Agent Order；支持 Checkpoint / Resume | Branch、Concurrency、Skip、Cancel、Policy Retry |
| Runtime | 基础可用 | Context Load、Relevance Selection、Workflow Resolve、Task Create / Resume、Failure Persistence | Approval API、Capability Discovery、Concurrency、Cancel |
| Task / Task Store | 基础可用 | Schema v2；Lifecycle、Current Agent、Resume Index、Event、Output、Error；Git-friendly Run Directory | Strict Agent I/O Schema、Migration、Diff、Replay、Search |
| Context Loader | 基础可用 | 读取 Project Config、Current Theme、Project Workflow、Resource 和 Markdown Memory | Historical Run、Approved Artifact、Tool Capability、Git Status、Source Hash |
| Context Retrieval | 基础可用 | Requirement + Active Theme 的确定性排序；英文 Token、中文 n-gram、Stopword、Budget、Score、Matched Term | Embedding Retrieval、Index、Dedup、Threshold Tuning、History Retrieval |
| Structured Planner | 基础可用 | Page、Dimension、Orientation、Engine、Theme、Reuse、Missing Resource、QA、Risk、Open Question | Typed Subtask、复杂 Component Tree、Interaction Flow、LLM Adapter |
| Structured Director | 基础可用 | Composition Zone、Focal Order、Memory Constraint、Reuse Decision、Conflict、Approval Point、Handoff | Complex Layout Reasoning、Reference Image Review、Cross-page Comparison、LLM Adapter |
| Structured Theme Agent | 基础可用 | Active Theme 解析；Preset 推导；Memory Constraint 合并；Conflict；状态管理 | Visual Token、Inheritance、Version、Reference、Approval / Materialization API |
| Structured Resource Agent | 基础可用 | Existing Reuse、Manifest Candidate、Dimension Provenance、Engine Import Hint、Conflict、Approval Point | Variant、Dependency、Atlas、Nine-slice、Reference Tracking、Materialization API |
| Structured Prompt Agent | 基础可用 | Provider-independent Prompt IR；Effect Image / Production Asset Job；Instruction；Constraint；Reference；Output Contract；Capability；Approval；Blocker；Provenance | Provider Adapter、Prompt Migration、Reference File Binding、Capability Negotiation |
| Structured Semantic QA Agent | 基础可用 | Prompt Schema、Provenance、Page、Theme、Resource Job、Reference、Execution Gate、Capability 检查；Finding、Revision Request、Artifact Review State 和 Export Gate | 尚无视觉 Artifact Inspection；缺少 Approval State、Artifact Binding、Cross-page / Usability QA 和 Revision Execution |
| Theme File Management | 基础可用 | 创建、激活和校验 Theme File | Migration、Inheritance、Version、Conflict Resolution |
| Resource Manifest | 可用 | Dimension、Format、Alpha、Naming、Target Engine、Import Hint | Variant、Atlas、Nine-slice、Dependency Graph |
| Memory | 基础可用 | Markdown Decision、Lesson、Mistake、Best Practice；Runtime 可读取和检索 | Auto Capture、Dedup、Priority、Expiry、Approval State |
| Asset QA | 可用 | 校验真实图片的 Dimension、Format、Alpha 和 Naming | Art Consistency、Layout、Readability、Multi-resolution QA |
| Protected Editing | 可用 | Mask Composition 并验证非目标像素 | 尚未进入 Runtime Revision Loop |
| Generation / Editing | 未开发 | Prompt IR 已准备，但 Runtime 尚未调用 Provider | Tool Adapter、Artifact Store、Reference Binding、Revision、Approval |
| Visual Semantic QA | 未开发 | 当前仅 Contract QA；Artifact Review 明确标记为 `not-run` | Image Inspection Adapter、Theme / Composition / Content / Usability Review |
| Export | 基础可用 | Generic / Unity / Godot / Unreal Adapter Metadata | Export Agent 仍是 Contract；Sidecar 不等于 Native Import；尚未消费 Export Gate |
| Host Integration | 未开发 | README 提供调用示例 | Stable Result Protocol、Pause、Approval、Streaming、Host Guide |
| Git Change Management | 未开发 | Git 是原则但 Runtime 不管理 Commit Lifecycle | Change Set、Branch / Commit、Rollback、Approval、Audit |

#### 2.1 当前可以真实完成的闭环

```text
Project Init
-> 创建 Theme、Workflow、Memory 和已有 Resource Manifest
-> 自然语言 Requirement 进入 Runtime
-> 加载完整 Context Snapshot
-> 选择相关 Context
-> Workflow 解析为 Pipeline
-> Planner 生成 Production Plan
-> Director 生成 Art Direction Review
-> Theme Agent 生成 Resolved Theme Contract
-> Resource Agent 生成 Resource Contract Bundle
-> Prompt Agent 生成 Model-neutral Prompt IR
-> Semantic QA 检查 Contract Consistency 与 Execution Gate
-> Task / Context / Selection / Event / Output 持久化
```

针对《韭菜派对》中世纪港口商店页，当前可以自动输出：

- Page Type、Canvas、Orientation 和 Target Engine；
- Theme Palette、Material、Lighting、Must Include 与 Avoid；
- 相关 Memory Constraint；
- Composition Zone、Focal Order 和 Interaction Rule；
- Existing Resource Reuse Decision；
- Missing Resource Manifest Candidate；
- Dimension Source 与 Engine Import Hint；
- Provider-independent Effect Image / Production Asset Job；
- Instruction、Negative Constraint、Reference、Output Contract 与 Acceptance Criteria；
- Prompt IR Contract Check；
- Blocking / Review / Info Finding；
- Revision Request、Artifact Review State 和 Export Gate；
- Approval Point、Blocker、Capability Requirement、Handoff、Risk 和 Provenance。

#### 2.2 当前尚不能完成的关键闭环

下面的自然语言需求仍不能仅靠 GUIF 自动完成全部生产：

```text
“为 LeekParty 制作一个符合现有中世纪港口风格的商店页面，
复用已有金币和按钮，生成缺失资源，检查后导出 Unity。”
```

GUIF 已能自动完成 Context Selection、Plan、Director Review、Theme Contract、Resource Contract Bundle、Prompt IR 和 Contract QA，但仍缺少 Approval API、Generation / Editing Adapter、Artifact Registration、视觉 Semantic QA、Revision Loop 和真实 Export Agent，因此尚不能自动产生视觉 Artifact 并交付完整 Engine-ready Output。

### 3. GUIF 预期待开发的内容

开发顺序以“尽快验证真实可用闭环”为原则，而不是继续增加空 Interface。

#### Phase 1：可审计、可恢复的 Runtime 基础

基础版本已完成：Task Lifecycle、Run Directory、Context / Event / Output / Error、Checkpoint、Load / List / Resume、Workflow / Pipeline 统一、Project Override、Agent Order 安全检查和 Persisted Context Selection。

仍待开发：Approval、Skip、Cancel、Retry Policy、Capability Discovery、Migration、Diff 和 Replay。

#### Phase 2：真实 Planner + Director

alpha.11 与 alpha.12 已完成第一版：结构化 Plan、Composition、Hierarchy、Reuse、Conflict、Approval Point 和 Handoff。

仍待开发：Typed Subtask、Complex Component Tree、Interaction Flow、Reference Image Review、Cross-page Comparison 与可替换 LLM Adapter。

#### Phase 3：Context 与 Memory Retrieval

alpha.12 已完成确定性基础版本。

仍待开发：Historical Task、Approved Artifact、Index、Dedup、Embedding Adapter、Source Hash、Priority 和 Context Size Policy。

#### Phase 4：Theme + Resource Production Contract

alpha.13 已完成第一版：Active Theme 解析、Preset 推导、Memory Constraint 合并、Validated Resource Manifest Candidate、Dimension Provenance、Engine Import Hint 和 Review-before-write。

仍待开发：Approval / Materialization API、Visual Token、Theme Inheritance、Variant、Dependency、Atlas、Nine-slice 与 Reference Graph。

#### Phase 5：Model-neutral Prompt IR

alpha.14 已完成第一版：Prompt IR schema v1、Global Contract、Effect Image / Production Asset Job、Structured Instruction、Negative Constraint、Reference、Output Contract、Capability Requirement、Approval Point、Blocker、Handoff 和 Provenance。

仍待开发：Provider Adapter、Prompt IR Migration、File / Image Reference Binding、Capability Negotiation、Provider-specific Rendering 和 Prompt Evaluation。

#### Phase 6：Semantic Contract QA

alpha.15 已完成第一版：

- Prompt IR Schema 检查；
- Upstream Output Provenance 检查；
- Page / Canvas / Orientation 一致性；
- Theme Must Include / Avoid 保留；
- Resource Candidate 与 Production Job 一一对应；
- Resource Output Contract 校验；
- Approved Reference Boundary；
- Review-before-execute Safety；
- Provider Capability Requirement；
- Finding、Revision Request、Artifact Review State 和 Export Gate；
- 没有视觉 Artifact 时明确记录 `not-run`，不产生虚假的视觉结论。

仍待开发：Artifact Registration、Visual Inspection Adapter、Cross-page Comparison、Readability、Usability、Artifact / Contract Binding 和 Revision Execution。

#### Phase 7：Approval API + State Transition

下一优先级。

目标：让 Human 或 Agent Host 能显式批准、拒绝或请求修改 Director、Theme、Resource 和 Prompt Approval Point。

需要包含：

- Stable Approval Record Schema；
- Approval ID、Decision、Actor、Reason 和 Timestamp；
- Approved Contract Hash / Snapshot；
- `review-required -> ready` 的受控转换；
- 拒绝后生成 Revision Request；
- Theme / Resource Materialization 仍需独立权限；
- Approval 不得自动调用 Provider；
- Resume 时使用已持久化 Approval State；
- CLI / Host API 用于 List、Show、Approve、Reject。

**验收标准**：同一个 LeekParty Task 可以列出全部 Required Approval，逐项持久化 Decision，并在全部满足后重新生成 `ready` Prompt IR；未批准内容不可执行。

#### Phase 8：Generation / Editing Adapter

目标：只执行已经批准且 `executable: true` 的 Prompt Job。

- Provider / Tool Capability Discovery；
- Prompt IR -> Provider Payload Adapter；
- Input Reference Binding；
- Artifact Store 和 Resource Manifest Link；
- Protected Edit Integration；
- Retry、Alternative、Cost / Quota Metadata 和 Human Approval。

#### Phase 9：Visual Semantic QA 与 Revision Loop

- Artifact / Prompt Job 双向引用；
- Theme、Composition、Content、Readability 和 UI Usability Review；
- Resource Output Contract Compliance；
- Cross-page Consistency；
- QA Finding -> Revision Task -> Recheck Loop；
- 所有视觉结论必须关联实际检查的 Artifact。

#### Phase 10：Production Export、Host 与 Git Integration

- Export Agent 消费 Passing Export Gate；
- Stable Host API / Result Protocol；
- Pause、Resume、Approval 与 Streaming；
- Native Engine Import；
- Git Change Set、Commit、Rollback 和 Audit；
- End-to-end Acceptance Test。

### 4. 开发决策门槛

任何新 Feature 开始前必须回答：

1. 是否直接服务 GUIF 产品定义？
2. 是否属于 Target Architecture 中明确职责？
3. 是否填补 Current State 中真实缺口？
4. 是否推进可验证的 End-to-end Loop，而不是增加空 Contract？
5. 是否定义 Test、Failure Behavior、Persistence、Approval 和 Acceptance Criteria？
6. 是否区分 Contract Verification 与 Artifact Verification？
7. 是否同步更新中英文 README、本文件和 Version Metadata？

答案不完整时，应先补 Product Decision，再写 Code。

### 5. 主要风险与待验证假设

- Rule-based Planner / Director / Theme 能否作为可维护的确定性 Fallback；
- Mutable Task 是否需要 Typed Subtask；
- Agent Granularity 应固定还是由 Project 定义；
- Workflow 是否应承担 Approval / Retry Policy；
- Project Workflow 变化后失败 Run 应迁移、冻结旧 Workflow 还是拒绝 Resume；
- Approval 应绑定 Contract Hash、完整 Snapshot 还是 Logical ID；
- Theme / Resource Approval 是否同时授权 Materialization；
- Prompt IR 的 `ready` 是否应由重建产生，还是允许原地修改；
- Provider Adapter 如何证明没有丢失 Negative Constraint、Output Contract 和 Provenance；
- Artifact 是否使用 File Store、Content-addressed Store 或外部 Connector；
- Visual QA 如何避免仅凭文字 Contract 推测视觉结果；
- Export Gate 如何与 Native Engine Import、Git Change 和 Human Approval 组合；
- 何时引入 Database，而不是继续使用 Git-friendly File Store；
- 如何避免 Framework 拥有大量 Schema，却没有完成真实生产闭环。

### 6. 迭代记录

#### `v1.0.0-alpha.9`

- 建立 Runtime、Task、Agent、Registry、Pipeline 和 Context Contract。

#### `v1.0.0-alpha.10`

- Task Schema v2；Task Store；Checkpoint；Structured Failure；Load、List 和 Resume。

#### `v1.0.0-alpha.11`

- Workflow schema v2；Workflow-driven Pipeline；第一个真实 Structured Planner Agent。

#### `v1.0.0-alpha.12`

- Relevance-based Context Selection；真实 Structured Director Agent。

#### `v1.0.0-alpha.13`

- 真实 Structured Theme 与 Resource Agent；Review-before-write。

#### `v1.0.0-alpha.14`

- Model-neutral Prompt IR schema v1；真实 Structured Prompt Agent；Review-before-execute。

#### `v1.0.0-alpha.15`

- 真实 Structured Semantic QA Agent；
- Prompt、Provenance、Page、Theme、Resource、Reference、Execution 和 Capability Contract 检查；
- Findings、Revision Request、Artifact Review State 和 Export Gate；
- 没有视觉 Artifact 时明确记录 `not-run`，不声称视觉 QA 已通过；
- 下一重点调整为 Approval API 与受控 State Transition。

---

## English Version

### 0. Purpose and maintenance rule

This file is GUIF's product definition, verified capability review, and iteration baseline. It is a living specification, not a one-time roadmap or marketing document.

It must be updated in the same release or pull request whenever product scope, architecture, core capability status, compatibility, priorities, risks, or open assumptions change.

A release is complete only when Feature, Test, CI, both READMEs, Version Metadata, and this specification agree.

### 1. Expected product

GUIF is an executable AI work framework for end-to-end game UI production. Natural language is the primary interface, ChatGPT or another Agent Host performs conversational orchestration, and Git plus Project files remain the long-term source of truth.

Expected flow:

```text
Requirement
  -> Context snapshot and retrieval
  -> Workflow and Pipeline
  -> Plan
  -> Art Direction Review
  -> Theme Contract
  -> Resource Contract Bundle
  -> Model-neutral Prompt IR
  -> Semantic Contract QA
  -> Human Approval
  -> Provider Adapter and Artifact
  -> Visual QA and Revision
  -> Export Gate and Engine-ready Output
```

Core principles:

- natural-language first;
- executable results rather than a Prompt Collection;
- model-agnostic Runtime and Prompt IR;
- isolated Project knowledge;
- deterministic production contracts;
- inspectable and recoverable Task Runs;
- review before write or execute;
- no visual-quality claim without an inspected visual Artifact;
- Git-backed long-term truth.

GUIF does not replace design tools or game engines, manage complete game code, train foundation models, become a general-purpose Agent Framework, or silently turn inferred values into approved production truth.

### 2. Verified state at alpha.15

GUIF can initialize Projects, load and retrieve Context, resolve Workflow-driven Pipelines, persist and resume Runs, and execute real deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents.

The Prompt Agent creates a provider-independent Prompt IR with Effect Image and Production Asset jobs, instructions, negative constraints, references, output contracts, capabilities, approval points, blockers, and provenance.

The Semantic QA Agent validates Prompt IR schema, upstream provenance, Page consistency, Theme constraint preservation, Resource job coverage, Resource output contracts, approved references, execution gates, and capability requirements. It produces structured Checks, Findings, a Revision Request, an Artifact Review state, and an explicit Export Gate.

Alpha.15 does not inspect visual Artifacts. When no Artifact exists, QA records `artifact_review.status: "not-run"` and keeps Export blocked. Contract QA therefore cannot be misrepresented as visual QA.

The main missing loop is now Approval -> Provider Adapter -> Artifact Registration -> Visual QA -> Revision -> Export.

### 3. Expected development

1. Implement an explicit Approval API and persisted Approval state transitions.
2. Rebuild review-required contracts into ready Prompt IR only after required approvals are satisfied.
3. Integrate Generation and Editing through Provider Adapters.
4. Register Artifacts with Prompt Job and Resource Contract provenance.
5. Add visual Semantic QA and Revision Loops.
6. Make the real Export Agent consume a passing Export Gate.
7. Add stable Host and Git change-management contracts.

The immediate acceptance target is a LeekParty Task whose required approvals can be listed, approved or rejected, persisted, audited, and used to produce a ready Prompt IR without implicitly modifying Project truth or calling a Provider.

### 4. Iteration gate

A Feature should not be implemented unless it serves the product definition, belongs to the target architecture, closes a verified capability gap, advances an end-to-end loop, defines Tests and Failure Behavior, separates Contract verification from Artifact verification, and updates all living documentation.

### 5. Main risks and open assumptions

Key unresolved questions include Task typing, Agent granularity, Workflow policy boundaries, approval identity and hash binding, materialization permissions, Prompt IR rebuild semantics, Provider constraint preservation, Artifact storage, visual-QA trust boundaries, Export Gate composition, file-store scalability, and the risk of accumulating schemas without proving a usable production loop.

### 6. Iteration history

- `alpha.9`: Runtime Contract, shared Task, Agent Registry, static Pipelines, and Context loading.
- `alpha.10`: Task schema v2, persistent Run Store, Agent checkpoints, structured failures, and resume APIs.
- `alpha.11`: Workflow-driven Pipelines and the first real Structured Planner Agent.
- `alpha.12`: relevance-based Context selection and the real Structured Director Agent.
- `alpha.13`: real Structured Theme and Resource Agents with review-before-write.
- `alpha.14`: model-neutral Prompt IR and the real Structured Prompt Agent with review-before-execute.
- `alpha.15`: real Structured Semantic QA Agent, Contract consistency checks, Findings, Revision Request, Artifact Review state, and Export Gate without false visual-verification claims.
