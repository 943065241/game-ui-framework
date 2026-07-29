# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.12`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅和后续迭代基线。它不是一次性 Roadmap，也不是宣传文案。

GUIF 每次发生下列变化时，本文件必须在同一个版本或同一个 Pull Request 中同步更新：

- 产品定位、边界或核心原则发生变化；
- 新增、替换或移除 Runtime、Task、Agent、Workflow、Pipeline、Context、Memory、Resource、QA、Export 等核心能力；
- 某项能力从 Contract / 占位升级为可实际完成工作；
- CLI、ChatGPT 接入方式、Project 目录或数据格式发生兼容性变化；
- 迭代优先级、已知风险或待验证假设发生变化。

一次 Release 只有在 Feature、Test、CI、英文 README、中文 README、Version Metadata 和本文件一致时才算完成。

### 1. GUIF 的预期

#### 1.1 一句话定义

GUIF 是一个以自然语言为主要入口、由 ChatGPT 或其他 Agent Host 调度、以 Git 和 Project File 作为长期事实来源、面向游戏 UI 生产全过程的可执行 AI 工作框架。

#### 1.2 预期用户体验

```text
用户：为《韭菜派对》制作中世纪港口商店页面，复用已有金币和按钮，检查后导出 Unity。

ChatGPT / Agent Host
  -> 选择 Project
  -> 调用 GUIF Runtime
  -> 加载 Project Context Snapshot
  -> 选择与当前 Requirement 相关的 Theme、Memory、Resource、Workflow 和历史 Run
  -> Planner 生成结构化 Production Plan
  -> Director 审阅 Composition、Hierarchy、Theme、Resource Reuse 和 Approval Point
  -> Theme / Resource Agent 形成可执行 Production Contract
  -> Prompt / Generation Agent 产生或修改视觉产物
  -> QA Agent 检查并驱动 Revision Loop
  -> Export Agent 交付 Engine-ready Output
  -> 保存 Task、Output、Decision、Report 和 Git Change
  -> 返回可审阅结果
```

CLI 保留用于开发、调试、自动化和 CI，但不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户描述目标，Framework 负责拆解和执行。
- **长期 Project Knowledge**：Theme、Decision、Lesson、Mistake 和 Best Practice 进入 Project 并由 Git 追踪。
- **可执行而非 Prompt Collection**：GUIF 必须产生结构化 Task、Plan、Review、文件、报告、Resource 和可验证结果。
- **Model Agnostic**：Runtime 不直接依赖单一模型或 Provider。
- **Project Isolation**：Framework Code 与具体游戏 Project 分离，不同 Project 的知识和资源互不污染。
- **Deterministic Production**：Naming、Dimension、Alpha、Export、Validation 和 Engine Adaptation 尽可能可重复。
- **可审计、可恢复**：每个 Run 应能回答读取了什么、选择了什么、执行到哪里、为什么失败、产生了什么，以及如何继续。

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
            -> Generation / Editing Agent
            -> QA Agent
            -> Export Agent
       -> Outputs + Reports + Memory + Git Changes
```

职责边界：

- **Agent Host**：理解对话、确认用户意图、调用 GUIF 并向用户解释结果。
- **Runtime**：加载 Context、执行相关性选择、解析 Workflow、创建或恢复 Task、调度 Agent、保存 Checkpoint 和处理失败；不包含具体美术业务逻辑。
- **Context Loader**：创建完整、可持久化的 Project Context Snapshot。
- **Context Retrieval**：从完整 Snapshot 中选择与当前 Requirement 相关的记录，并保留 Score、Matched Term、Budget 和 Provenance。
- **Workflow**：项目级与内置的可执行流程事实来源，声明人类可读步骤和 Agent 顺序。
- **Pipeline**：Workflow 在一次 Run 中的解析结果，负责按顺序执行 Agent 并定义恢复位置。
- **Task Store**：持久化 Task Snapshot、Context Snapshot、Event、Output 和 Error。
- **Agent**：完成单一职责；Agent 不直接调用其他 Agent。
- **Task**：贯穿执行过程的统一状态、事件、输入、输出和错误载体。
- **Git**：长期事实来源、变更记录和协作边界。

#### 1.5 非目标

GUIF 不计划：

- 替代 Photoshop、Figma、Unity、Godot 或 Unreal；
- 管理完整游戏逻辑、Server、数值或关卡代码；
- 训练基础模型；
- 成为任意行业的通用 Agent Framework；
- 将所有 AI 和 Tool Logic 塞进 Runtime；
- 用不可追踪的 Chat Memory 替代 Project File 和 Git。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.12` 仓库代码。

状态定义：

- **可用**：已经能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：目标明确，但仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录和 `project.json`；Project 包含 `runs/` | Migration、Template、Archive 和 Schema Upgrade |
| Legacy Requirement Routing / Plan | 基础可用 | Keyword Routing 并生成 Routed Plan JSON | 与 Runtime Planner 并存；最终需要明确迁移或废弃策略 |
| Workflow | 基础可用 | Schema v2 声明 `steps` 与 `agents`；Built-in / Project Override；v1 兼容 | Condition、Loop、Error Policy、Approval Gate 和 Migration Tool |
| Pipeline | 基础可用 | Runtime 从 Workflow 构建 Pipeline；保存 Source、Manager、Steps 和 Agent Order；Checkpoint 与 Resume | Declarative Branch、Concurrency、Skip、Cancel 和 Policy Retry |
| Runtime | 基础可用 | Context Load、Relevance Selection、Workflow Resolve、Task Create / Resume、Checkpoint 和 Failure Persistence | Approval、Capability Discovery、Concurrency、Policy Retry 和 Cancel |
| Task | 基础可用 | Schema v2；Status、Current Agent、Resume Index、State、Event、Output、Error 和 Timestamp | 严格 Agent Input / Output Contract、Schema Validation 和 Migration Tool |
| Task Store / Run History | 基础可用 | `task.json`、`context.json`、`events.jsonl`、`outputs.json`、失败时 `error.json` | Run Diff、Replay、Retention、Search 和可视化审计 |
| Context Loader | 基础可用 | 读取 Project Config、Current Theme、Project Workflow、Resource 和 Markdown Memory；保存完整 Snapshot | Historical Task、Approved Artifact、Tool Capability、Git Status 和 Source Hash |
| Context Retrieval | 基础可用 | Requirement + Active Theme 的确定性相关性排序；英文 Token、中文 n-gram、Stopword、Budget、Score 和 Matched Term | 不是 Embedding Semantic Retrieval；缺少 Threshold Tuning、Index、Dedup、History Retrieval 和 Provenance Hash |
| Structured Planner | 基础可用 | 真实 Agent；识别 Page、Dimension、Orientation、Engine、Theme、Reuse、Missing Resource、QA、Risk 和 Open Question | Rule Coverage 有限；缺少 Typed Subtask、复杂组件树、交互流和 LLM Planner Adapter |
| Structured Director | 基础可用 | 真实 Agent；生成 Composition Zone、Focal Order、Theme Contract、Memory Constraint、Reuse Decision、Conflict、Approval Point 和 Handoff | Template Coverage 有限；缺少复杂 Layout Reasoning、Reference Image Review、Cross-page Comparison 和 LLM Director Adapter |
| Theme | 基础可用 | 创建、激活、校验 Theme；Planner 与 Director 读取 Theme Contract | Theme Agent 仍是 Contract；缺少 Structured Visual Token、Inheritance、Version 和 Conflict Resolution |
| Memory | 基础可用 | 记录 Markdown Decision、Lesson、Mistake、Best Practice；Runtime 可读取并检索 | 缺少自动沉淀、Deduplication、Priority、Expiry 和 Approval State |
| Resource Contract | 可用 | Manifest、Dimension、Format、Alpha、Naming、Target Engine 和 Import Hint | Resource Agent 仍是 Contract；缺少 Dependency、Variant、Atlas、Nine-slice 和 Reference Tracking |
| Asset QA | 可用 | 校验真实 Image Asset 的 Dimension、Format、Alpha 和 Naming | Semantic、Art Consistency、Layout、Readability 和 Multi-resolution QA |
| Protected Editing | 可用 | Mask Composition 并验证非目标像素未变化 | 尚未进入 Runtime 自动修图循环 |
| Export | 基础可用 | Deterministic Validation、Copy、Report 和 Generic / Unity / Godot / Unreal Metadata | Export Agent 仍是 Contract；Sidecar 不等于 Native Engine Import |
| Agent Interface | 基础可用 | Agent 接收并返回同一个 Task；Planner 与 Director 执行真实领域工作 | Theme、Resource、Prompt、QA、Export 仍只记录 Contract Behavior |
| Prompt Builder | 未开发 | 只有 Prompt Agent Contract | Model-neutral Prompt IR、Template Composition、Negative Constraint 和 Version Record |
| Generation / Editing | 未开发 | Runtime 尚未调用 Image Generation、Figma 或其他 Production Tool | Provider / Tool Adapter、Artifact Registration 和 Revision Loop |
| Semantic QA | 未开发 | 无真实 Agent-level Semantic Check | Theme、Composition、Content、UI Usability 和 Cross-page Consistency QA |
| ChatGPT Integration Contract | 未开发 | README 描述预期调用关系 | Stable Machine Interface、Result Protocol 和 Host Guide |
| Git Change Management | 未开发 | Git 是原则，但 Runtime 不管理 Commit Lifecycle | Change Set、Branch / Commit Strategy、Rollback 和 Human Approval |

#### 2.1 当前可以真实完成的闭环

```text
Project Init
-> 创建 Theme、Workflow、Memory 和 Resource Manifest
-> 自然语言 Requirement 进入 Runtime
-> 加载完整 Context Snapshot
-> 选择相关 Memory / Resource / Workflow
-> Workflow 解析为 Pipeline
-> Planner 生成结构化 UI Production Plan
-> Director 生成 Art Direction Review
-> Task / Context / Selection / Event / Output 持久化
-> 可选 Asset Validation 与 Protected Edit
-> 手工调用 Engine Adapter Export
```

针对《韭菜派对》中世纪港口商店页，GUIF 现在可以输出：

- Page Type、Canvas、Orientation 和 Target Engine；
- Theme Must Include 与 Avoid；
- Existing Resource Reuse Candidate；
- Missing Resource Suggestion；
- 相关 Memory Constraint；
- Composition Zone、Focal Order 和 Interaction Rule；
- Conflict、Approval Point、QA Handoff、Risk 和 Open Question。

#### 2.2 当前尚不能完成的关键闭环

下面这句自然语言仍不能仅靠 GUIF 自动完成全部生产：

```text
“为 LeekParty 制作一个符合现有中世纪港口风格的商店页面，
复用已有金币和按钮，生成缺失资源，检查后导出 Unity。”
```

GUIF 已能自动完成 Context Selection、Plan 和 Director Review，但 Theme、Resource、Prompt、Generation、Semantic QA 和 Export Agent 尚未形成真实自动生产链，因此还不能自动生成视觉产物、循环修订并交付完整 Engine-ready Output。

### 3. GUIF 预期待开发的内容

开发顺序以“尽快验证真实可用闭环”为原则，而不是继续扩充空 Interface。

#### Phase 1：可审计、可恢复的 Runtime 基础

已完成基础版本：

- Task Schema v2 和 Lifecycle；
- Git-friendly Run Directory；
- Context、Event、Output 和 Error 持久化；
- Agent 前后 Checkpoint；
- Load、List、Resume；
- Workflow 与 Pipeline 统一；
- Project Workflow Override；
- Resume 时检查 Agent Order；
- 失败 Run 使用已持久化的 Context Selection。

仍待开发：

- Declarative Error / Retry Policy；
- Human Approval、Skip 和 Cancel；
- Runtime Capability Discovery；
- Run Migration、Diff 和 Replay。

#### Phase 2：真实 Planner + Director

alpha.12 已完成第一版：

- Structured Planner Agent；
- Structured Director Agent；
- Stable Plan 和 Art Direction Review Schema；
- Page / Canvas / Engine / Theme / Resource / QA / Risk / Open Question；
- Composition / Hierarchy / Memory Constraint / Reuse Decision / Conflict / Approval / Handoff；
- Plan 与 Review 写入 Task State 和 Output Index。

仍待开发：

- Typed Page、Component 和 Subtask；
- Complex Interaction Flow；
- Reference Image Analysis；
- Cross-page Coherence；
- LLM Planner / Director Adapter；
- Planner 与 Director Conflict Resolution 和 Human Approval State。

#### Phase 3：Context 与 Memory Retrieval

alpha.12 已完成第一版：

- Markdown Memory 实际加载；
- Requirement 与 Active Theme 共同构造 Query Term；
- 英文 Token 和中文 n-gram；
- Stopword Filter；
- Memory / Resource / Workflow Ranking；
- Budget、Score、Matched Term、Total 和 Omitted Count；
- Context Selection 持久化到 Task State。

仍待开发：

- Historical Task 和 Approved Artifact Retrieval；
- Source Hash、Provenance 和 Snapshot Version；
- Index、Threshold、Deduplication 和 Priority；
- Theme / Resource Reference Graph；
- Context Size Budget 与 Agent-specific Selection；
- Embedding 或外部 Retriever Adapter。

#### Phase 4：真实 Theme + Resource Agent

目标：把 Planner 与 Director 的结果转换成可执行 Production Contract。

- Theme Agent 解析、补全和校验 Visual Token；
- Theme Conflict、Inheritance 和 Version；
- Resource Agent 创建或更新 Resource Manifest；
- Reuse / Replace / New Resource 决策落盘；
- Dimension、Alpha、Naming、Engine Target 和 Source Link；
- Atlas、Variant、Nine-slice 和 Dependency Contract；
- Human Approval 后才允许覆盖已批准 Resource。

**阶段验收标准**：LeekParty 商店页 Run 能根据 Plan 和 Director Review，自动生成缺失 Resource Manifest，同时保留已批准的金币和按钮 Contract。

#### Phase 5：Model-neutral Prompt IR

- Positive Requirement、Negative Constraint、Reference、Dimension 和 Output Contract；
- Provider Adapter；
- Prompt Version 和 Provenance；
- Prompt 与 Generated Artifact 的双向引用。

#### Phase 6：Generation / Editing Tool Adapter

- Tool Capability Discovery；
- Input / Output Adapter；
- Artifact Store 和 Resource Manifest Link；
- Protected Edit Integration；
- Retry、Alternative 和 Human Approval。

#### Phase 7：Semantic QA 与 Revision Loop

- Theme Consistency；
- Composition、Readability 和 UI Usability；
- Cross-page Consistency；
- Resource Contract Compliance；
- QA Finding -> Revision Task -> Recheck Loop。

#### Phase 8：Production Export、Host 与 Git Integration

- Stable Host API / Result Protocol；
- Human Approval Point；
- Native Engine Import Integration；
- Git Change Set、Commit、Rollback 和 Audit；
- End-to-end Acceptance Test。

### 4. 开发决策门槛

任何新 Feature 开始前必须回答：

1. 它是否直接服务 GUIF 的产品定义？
2. 它是否属于 Target Architecture 中明确的职责？
3. 它是否填补 Current State 中的真实缺口？
4. 它是否推进一个可验证的 End-to-end Loop，而不只是增加 Contract？
5. 是否定义了 Test、Failure Behavior、Persistence 和 Acceptance Criteria？
6. 是否同步更新英文 README、中文 README 和本文件？

如果答案不完整，应先补充 Product Decision，再写 Code。

### 5. 主要风险与待验证假设

- Rule-based Planner 和 Director 能否作为 LLM Agent 的稳定 Fallback，而不是演变成难维护的 Template / Keyword Collection；
- Lexical / n-gram Retrieval 是否会遗漏语义相关记录，或因 Active Theme 词项造成过度匹配；
- Memory Constraint Marker 提取是否会误解上下文、否定关系或已经失效的旧 Decision；
- 一个 Mutable `Task` 是否足以承载所有 UI Production 类型，还是需要 Typed Subtask；
- Agent Granularity 应固定，还是允许 Project 定义；
- Workflow v2 是否足以承担 Pipeline Source of Truth，还是需要独立 Execution Policy；
- Project Workflow 变化后，失败 Run 应迁移、冻结旧 Workflow，还是拒绝 Resume；
- Resume 应永远使用原 Context Selection，还是允许显式 Refresh 并生成 Diff；
- Prompt Builder 应是 Core Capability，还是 Plugin；
- ChatGPT 是否始终是主要 Host，还是需要独立 Service API；
- Context Snapshot 和 Selection 保存完整内容、Hash，还是受控 Reference；
- Failure Retry 是否要求 Agent 提供 Idempotency Contract；
- 何时引入 Database，而不是继续使用 Git-friendly File Store；
- 如何防止 Framework 变成拥有大量 Interface、但没有完整生产闭环的架构样板。

### 6. 迭代记录

#### `v1.0.0-alpha.9`

- 建立 Runtime、Task、Agent、Registry 和 Pipeline Contract；
- Built-in Agent 为 Contract-level Behavior；
- Context Loader 读取 Project Config、Theme、Workflow、Resource 和 Memory。

#### `v1.0.0-alpha.10`

- Task Schema v2；
- Lifecycle、Current Agent、Resume Index 和 Structured Error；
- Task Store、Checkpoint、Load、List 和 Resume；
- CLI 新增 `run-list`、`run-show`、`run-resume`。

#### `v1.0.0-alpha.11`

- Workflow schema v2 与 Workflow-driven Pipeline；
- Project Workflow Override 和安全 Resume 检查；
- Structured Planner Agent；
- UI Production Plan Schema、Theme Constraint、Resource Reuse、Missing Resource、QA、Risk 和 Open Question；
- 修复 Markdown Memory 未实际加载的问题。

#### `v1.0.0-alpha.12`

- 新增确定性 Context Retrieval；
- 支持英文 Token、中文 n-gram、Stopword、Budget、Score 和 Matched Term；
- Memory、Resource 和 Project Workflow Selection 写入 Task State；
- Resume 保留原 Context Selection；
- Structured Director Agent 替换 Director Contract；
- 新增 Art Direction Review Schema；
- 生成 Composition Zone、Focal Order、Theme Contract、Memory Constraint、Resource Reuse Decision、Conflict、Approval Point 和 Handoff；
- 新增 Retrieval 与 Director Test；
- 下一重点调整为 Real Theme Agent 与 Resource Agent。

---

## English Version

### 0. Purpose and maintenance rule

This file is GUIF's product definition, verified capability review, and iteration baseline. It is a living specification, not a one-time Roadmap or marketing document.

It must be updated in the same release or Pull Request whenever product scope, architecture, core capability status, compatibility, priorities, risks, or open assumptions change.

A Release is complete only when Feature, Test, CI, both READMEs, Version Metadata, and this specification agree.

### 1. Expected product

GUIF is an executable AI work framework for end-to-end game UI production. Natural language is the primary interface, ChatGPT or another Agent Host performs conversational orchestration, and Git plus Project files remain the long-term source of truth.

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
       -> Outputs, Reports, Memory, and Git Changes
```

Core principles:

- natural-language first;
- executable results rather than a Prompt Collection;
- model-agnostic Runtime orchestration;
- isolated Project knowledge;
- deterministic production contracts;
- focused and auditable Context selection;
- inspectable and recoverable Task Runs;
- Git-backed long-term truth.

GUIF does not replace design tools or game engines, manage complete game code, train foundation models, or become a general-purpose Agent Framework.

### 2. Verified state at alpha.12

GUIF can initialize Projects, manage Themes and Resource Contracts, read Markdown Memory, validate Image Assets, protect non-target pixels, export deterministic Engine Adapter metadata, persist and resume Runs, and execute Workflow-driven Pipelines.

Runtime now creates a deterministic Context selection for each Requirement. It ranks Memory, Resource manifests, and Project Workflow manifests using Requirement terms and semantic values from the active Theme. English Tokens, Chinese n-grams, Stopword filtering, budgets, scores, matched terms, totals, and omitted counts are recorded in `Task.state["context_selection"]`.

Planner and Director are now real built-in domain Agents. Planner creates a validated UI Production Plan. Director consumes that Plan and creates a validated Art Direction Review containing composition zones, focal order, Theme rules, Memory-derived constraints, Resource reuse decisions, conflicts, approval points, and downstream handoffs.

The principal limitation has moved downstream: Theme, Resource, Prompt, QA, Export, and Generation remain Contract-only or unimplemented. GUIF still cannot automatically create visual assets, run semantic revision loops, and deliver complete Engine-ready output from one Requirement.

### 3. Expected development

1. Finish Runtime policies: approval, retry, cancel, capability discovery, migration, diff, and replay.
2. Extend Planner and Director with typed subtasks, interaction flows, reference review, and optional LLM Adapters.
3. Extend Context Retrieval with history, approved artifacts, provenance hashes, indexes, thresholds, deduplication, and Agent-specific budgets.
4. Implement real Theme and Resource Agents that produce or update executable Production Contracts.
5. Define a model-neutral Prompt IR.
6. Integrate Generation and Editing tools through Adapters.
7. Implement Semantic QA and Revision Loops.
8. Add stable Agent Host, native Engine, and Git change-management contracts.

The immediate acceptance target is now the next step of the LeekParty medieval-harbor shop page: GUIF should turn the approved Plan and Director Review into concrete Theme and Resource manifests while preserving approved reusable coins and buttons.

### 4. Iteration gate

A Feature should not be implemented unless it serves the product definition, belongs to the target architecture, closes a verified capability gap, advances an End-to-end Loop, defines Tests and Failure Behavior, and updates all living documentation.

### 5. Main risks and open assumptions

Key unresolved questions include maintainability of rule-based Planner and Director fallbacks, lexical Retrieval quality, Memory constraint interpretation, Task typing, Agent granularity, Workflow policy boundaries, resume behavior after Workflow or Context changes, Prompt Builder ownership, Host strategy, Context snapshot semantics, retry idempotency, file-store scalability, and the risk of accumulating interfaces without proving a usable production loop.

### 6. Iteration history

- `alpha.9`: Runtime Contract, shared Task, Agent Registry, static Pipelines, and Context loading.
- `alpha.10`: Task schema v2, persistent Run Store, Agent checkpoints, structured failures, and load/list/resume APIs.
- `alpha.11`: Workflow schema v2, Workflow-driven Pipelines, Project overrides, safe-resume checks, Structured Planner, and real Markdown Memory loading.
- `alpha.12`: deterministic Context Retrieval, persisted Context selection, and a real Structured Director Agent with validated Art Direction Reviews.
