# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.14`  
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
  -> Human / Host 审批 Approval Point
  -> Generation / Editing Adapter 产生 Artifact
  -> QA Agent 检查并驱动 Revision Loop
  -> Export Agent 交付 Engine-ready Output
  -> 保存 Task、Output、Decision、Report 和 Git Change
```

CLI 保留用于开发、调试、自动化和 CI，但不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户描述目标，Framework 负责拆解、约束和执行。
- **长期 Project Knowledge**：Theme、Decision、Lesson、Mistake 和 Best Practice 由 Project File 与 Git 追踪。
- **可执行而非 Prompt Collection**：GUIF 必须产生结构化 Task、Plan、Review、Contract、Prompt IR、Artifact 和可验证结果。
- **Model Agnostic**：Runtime 与 Prompt IR 不直接依赖单一模型或 Provider。
- **Project Isolation**：Framework Code 与具体游戏 Project 分离。
- **Deterministic Production**：Naming、Dimension、Alpha、Validation、Export 和 Engine Adaptation 尽可能可重复。
- **可审计、可恢复**：每个 Run 必须说明读取了什么、选择了什么、执行到哪里、产生了什么、为什么失败以及如何继续。
- **Review Before Write / Execute**：推导结果未经批准，不得成为 Project Truth，也不得自动提交给 Provider 执行。

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
            -> Generation / Editing Adapter
            -> QA Agent
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
- **Provider Adapter**：将已批准 Prompt IR 转换为具体 Tool / Model 调用，并登记 Artifact。
- **Git**：长期事实来源、变更记录和协作边界。

#### 1.5 非目标

GUIF 不计划：

- 替代 Photoshop、Figma、Unity、Godot 或 Unreal；
- 管理完整游戏逻辑、Server、数值或关卡代码；
- 训练基础模型；
- 成为任意行业的通用 Agent Framework；
- 将全部 AI 与 Tool Logic 塞进 Runtime；
- 用不可追踪的 Chat Memory 替代 Project File 与 Git；
- 在没有明确 Review / Approval 的情况下把推导结果写入 Project 或提交给 Provider。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.14` 仓库代码。

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
| Structured Theme Agent | 基础可用 | Active Theme 解析；Preset 推导；Memory Constraint 合并；Conflict；`ready / review-required / blocked` | Visual Token、Inheritance、Version、Reference、Approval / Materialization API |
| Structured Resource Agent | 基础可用 | Existing Reuse、Manifest Candidate、Dimension Provenance、Engine Import Hint、Conflict、Approval Point | Variant、Dependency、Atlas、Nine-slice、Reference Tracking、Materialization API |
| Structured Prompt Agent | 基础可用 | Provider-independent Prompt IR；Effect Image / Production Asset Job；Instruction Group；Negative Constraint；Reference；Output Contract；Capability；Approval；Blocker；Provenance | Provider Adapter、Prompt Version Migration、Reference File Binding、Provider Capability Negotiation |
| Theme File Management | 基础可用 | 创建、激活和校验 Theme File | Migration、Inheritance、Version、Conflict Resolution |
| Resource Manifest | 可用 | Dimension、Format、Alpha、Naming、Target Engine、Import Hint | Variant、Atlas、Nine-slice、Dependency Graph |
| Memory | 基础可用 | Markdown Decision、Lesson、Mistake、Best Practice；Runtime 可读取和检索 | Auto Capture、Dedup、Priority、Expiry、Approval State |
| Asset QA | 可用 | 校验真实图片的 Dimension、Format、Alpha 和 Naming | Semantic、Art Consistency、Layout、Readability、Multi-resolution QA |
| Protected Editing | 可用 | Mask Composition 并验证非目标像素 | 尚未进入 Runtime Revision Loop |
| Generation / Editing | 未开发 | Prompt IR 已准备，但 Runtime 尚未调用 Provider | Tool Adapter、Artifact Store、Reference Binding、Revision、Approval |
| Semantic QA | 未开发 | QA Agent 仍为 Contract | Theme、Composition、Usability、Cross-page Consistency、Prompt IR / Artifact Review |
| Export | 基础可用 | Generic / Unity / Godot / Unreal Adapter Metadata | Export Agent 仍是 Contract；Sidecar 不等于 Native Import |
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
-> Task / Context / Selection / Event / Output 持久化
-> 可选 Asset Validation、Protected Edit 与手工 Export
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
- Approval Point、Blocker、Capability Requirement、Handoff、Risk 和 Provenance。

#### 2.2 当前尚不能完成的关键闭环

下面的自然语言需求仍不能仅靠 GUIF 自动完成全部生产：

```text
“为 LeekParty 制作一个符合现有中世纪港口风格的商店页面，
复用已有金币和按钮，生成缺失资源，检查后导出 Unity。”
```

GUIF 已能自动完成 Context Selection、Plan、Director Review、Theme Contract、Resource Contract Bundle 和 Prompt IR，但仍缺少 Approval API、Generation / Editing Adapter、Artifact Registration、Semantic QA、Revision Loop 和真实 Export Agent，因此尚不能自动产生视觉 Artifact 并交付完整 Engine-ready Output。

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

alpha.14 已完成第一版：

- Prompt IR schema v1；
- Provider Binding Placeholder；
- Global Page / Composition / Theme Contract；
- Effect Image Job 与 Production Asset Job；
- Structured Instruction Group；
- Negative Constraint、Reference 和 Output Contract；
- Capability Requirement；
- Approval Point、Blocker、Handoff 和 Provenance；
- `ready / review-required / blocked`；
- 非 `ready` Job 禁止自动执行。

仍待开发：Provider Adapter、Prompt IR Migration、File / Image Reference Binding、Capability Negotiation、Provider-specific Rendering 和 Prompt Evaluation。

#### Phase 6：Generation / Editing Adapter

目标：只执行已经批准且 `executable: true` 的 Prompt Job。

- Provider / Tool Capability Discovery；
- Prompt IR -> Provider Payload Adapter；
- Input Reference Binding；
- Artifact Store 和 Resource Manifest Link；
- Protected Edit Integration；
- Retry、Alternative、Cost / Quota Metadata 和 Human Approval。

#### Phase 7：Semantic QA 与 Revision Loop

下一优先级：

- Prompt IR Contract QA；
- Theme、Composition、Content 和 UI Usability Review；
- Resource Output Contract Compliance；
- Cross-page Consistency；
- QA Finding -> Revision Task -> Recheck Loop；
- 无视觉 Artifact 时，QA 只审阅 Contract，不虚构视觉结论。

#### Phase 8：Production Export 与 Host Integration

- Stable Host API / Result Protocol；
- Human Approval / Pause / Resume；
- Native Engine Import Integration；
- Git Change Set、Commit、Rollback 和 Audit；
- End-to-end Acceptance Test。

### 4. 开发决策门槛

任何新 Feature 开始前必须回答：

1. 是否直接服务 GUIF 产品定义？
2. 是否属于 Target Architecture 中明确职责？
3. 是否填补 Current State 的真实缺口？
4. 是否推进可验证的 End-to-end Loop，而不是只增加 Contract？
5. 是否定义 Test、Failure Behavior、Persistence、Approval 和 Acceptance Criteria？
6. 是否同步更新中英文 README、Version Metadata 和本文件？

### 5. 主要风险与待验证假设

- Rule-based Agent 能否保持为稳定 Fallback，而不是演变为难维护的 Keyword Collection；
- Mutable `Task` 是否需要 Typed Subtask；
- Agent Granularity 应固定还是允许 Project 定义；
- Prompt IR schema v1 是否能覆盖 Image Generation、Image Editing、Figma 与未来 Tool；
- Approval 应修改原 Task、创建新 Task，还是产生独立 Decision Record；
- Provider Adapter 如何声明 Idempotency、Cost、Quota、Safety 与 Capability；
- Reference 应保存 File、Hash、URI 还是 Artifact ID；
- Context Snapshot 与 Prompt IR 的 Source Hash 如何保证 Resume / Replay 可重复；
- 何时引入 Database，而不是继续使用 Git-friendly File Store；
- 如何避免接口持续增加但真实视觉生产闭环仍不可用。

### 6. 迭代记录

- `alpha.9`：Runtime、Task、Agent Registry、Pipeline 与 Context Contract。
- `alpha.10`：Task schema v2、Run Store、Checkpoint、Failure、Load / List / Resume。
- `alpha.11`：Workflow-driven Pipeline 与第一个真实 Structured Planner Agent。
- `alpha.12`：Context Retrieval 与真实 Structured Director Agent。
- `alpha.13`：真实 Structured Theme / Resource Agent 与 Review-before-write。
- `alpha.14`：真实 Structured Prompt Agent、Prompt IR schema v1、Provider-independent Job、Approval / Blocker / Capability / Provenance，以及非 `ready` Job 禁止执行。

---

## English Version

### 0. Purpose and maintenance

This living specification defines GUIF's product, verified state, capability gaps, and iteration priorities. It must change in the same release or pull request whenever product scope, architecture, compatibility, capability status, risk, or priority changes.

A release is complete only when Feature, Test, CI, both READMEs, Version Metadata, and this specification agree.

### 1. Expected product

GUIF is an executable AI work framework for end-to-end game UI production. Natural language is the primary interface, ChatGPT or another Agent Host performs conversational orchestration, and Git plus Project files remain the long-term source of truth.

Expected flow:

```text
User
  -> Agent Host
  -> Runtime
  -> Context Load and Retrieval
  -> Workflow and Pipeline
  -> Planner
  -> Director
  -> Theme Contract
  -> Resource Contract Bundle
  -> Model-neutral Prompt IR
  -> Approval
  -> Generation / Editing Adapter
  -> Semantic QA and Revision
  -> Export, Memory, and Git Changes
```

Prompt IR is a provider-independent contract, not an OpenAI, image-model, or Figma payload. Inferred results require review before Project mutation or Provider execution.

GUIF does not replace design tools or game engines, manage complete game code, train foundation models, or become a general-purpose Agent Framework.

### 2. Verified state at alpha.14

GUIF can initialize Projects, load and retrieve Project Context, resolve Workflow-driven Pipelines, persist and resume Runs, and execute real deterministic Planner, Director, Theme, Resource, and Prompt Agents.

Prompt IR schema v1 now records global composition and Theme contracts, Effect Image and Production Asset jobs, structured instruction groups, negative constraints, approved references, exact output contracts, acceptance criteria, capability requirements, approval points, blockers, handoff instructions, and provenance. Provider and model IDs remain unbound. Jobs are executable only when IR status is `ready`.

The main remaining gap is execution and evaluation: GUIF still lacks an Approval API, Provider Adapter, Artifact Store, Semantic QA, Revision Loop, and real Export Agent.

### 3. Expected development

1. Add Approval, pause, cancel, and capability policies to Runtime.
2. Implement Provider Adapters that translate approved Prompt IR without losing structured contracts.
3. Register generated or edited Artifacts with references, hashes, Resource links, and provenance.
4. Implement Semantic QA for Prompt IR and Artifacts, then a Revision Loop.
5. Complete native Engine export, Host Result Protocol, and Git change management.

The immediate next target is a real QA Agent. Before visual Artifacts exist, it must review Prompt IR contracts only and must not invent visual conclusions.

### 4. Iteration gate

A Feature should not be implemented unless it serves the product definition, belongs to the target architecture, closes a verified gap, advances an end-to-end loop, defines Tests and Failure Behavior, respects Approval and Persistence, and updates all living documentation.

### 5. Main risks

Key unresolved questions include deterministic-rule maintainability, Task typing, Agent granularity, Prompt IR coverage, Approval state modeling, Provider capability and idempotency contracts, reference identity, reproducible Resume / Replay, file-store scalability, and the risk of accumulating interfaces without proving real visual production.

### 6. Iteration history

- `alpha.9`: Runtime and Agent contracts.
- `alpha.10`: persistent and resumable Runs.
- `alpha.11`: Workflow-driven Pipelines and Structured Planner.
- `alpha.12`: Context Retrieval and Structured Director.
- `alpha.13`: Structured Theme and Resource contracts with review-before-write.
- `alpha.14`: model-neutral Prompt IR, structured generation jobs, Provider placeholders, capability requirements, Approval Points, Blockers, Provenance, and non-ready execution gating.
