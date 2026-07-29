# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.11`  
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

用户主要表达目标，而不是手工操作底层命令：

```text
用户：为《韭菜派对》制作中世纪港口商店页面。

ChatGPT / Agent Host
  -> 选择 Project
  -> 调用 GUIF Runtime
  -> 读取与任务相关的 Theme、Workflow、Resource、Memory 和历史 Run
  -> 生成结构化 Plan
  -> 审阅 Art Direction 与 Resource Reuse
  -> 调用适合的 Model 或 Tool
  -> 自动 QA、修订和 Export
  -> 保存 Task、Output、Decision 和 Git Change
  -> 返回可审阅结果
```

CLI 保留用于开发、调试、自动化和 CI，但不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户描述目标，Framework 负责拆解和执行。
- **长期 Project Knowledge**：Theme、Decision、Lesson、Mistake 和 Best Practice 进入 Project 并由 Git 追踪。
- **可执行而非 Prompt Collection**：GUIF 必须产生结构化 Task、Plan、文件、报告、Resource 和可验证结果。
- **Model Agnostic**：Runtime 不直接依赖单一模型或 Provider。
- **Project Isolation**：Framework Code 与具体游戏 Project 分离，不同 Project 的知识和资源互不污染。
- **Deterministic Production**：Naming、Dimension、Alpha、Export、Validation 和 Engine Adaptation 尽可能可重复。
- **可审计、可恢复**：每个 Run 应能回答读取了什么、执行到哪里、为什么失败、产生了什么，以及如何继续。

#### 1.4 目标架构

```text
User
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> Context Loader / Retrieval
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
- **Runtime**：加载 Context、解析 Workflow、创建或恢复 Task、调度 Agent、保存 Checkpoint 和处理失败；不包含具体美术业务逻辑。
- **Workflow**：项目级与内置的可执行流程事实来源，声明人类可读步骤和 Agent 顺序。
- **Pipeline**：Workflow 在一次 Run 中的解析结果，负责按顺序执行 Agent 并定义恢复位置。
- **Task Store**：持久化 Task Snapshot、Context Snapshot、Event、Output 和 Error。
- **Agent**：完成单一职责；Agent 不直接调用其他 Agent。
- **Task**：贯穿执行过程的统一状态、事件、输入、输出和错误载体。
- **Context**：Project Config、Theme、Workflow、Resource、Memory、History 和环境能力的只读 Snapshot 或受控引用。
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

以下结论基于 `v1.0.0-alpha.11` 仓库代码。

状态定义：

- **可用**：已经能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：目标明确，但仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录和 `project.json`；Project 包含 `runs/` | Migration、Template、Archive 和 Schema Upgrade |
| Legacy Requirement Routing / Plan | 基础可用 | Keyword Routing 并生成 Routed Plan JSON | 不是 Context-aware Planning；与 Runtime Planner 是两条并存路径 |
| Workflow | 基础可用 | Schema v2 声明 `steps` 与 `agents`；Built-in / Project Override；v1 兼容推导 Agent 顺序 | 缺少 Condition、Loop、Error Policy、Approval Gate 和 Migration Tool |
| Pipeline | 基础可用 | Runtime 从 Workflow 构建 Pipeline；保存 Source、Manager、Steps、Agent Order；Checkpoint 与 Resume | 缺少 Declarative Branch、Concurrency、Skip、Cancel 和 Policy Retry |
| Structured Planner | 基础可用 | 第一个真实 Agent；规则化识别 Page、Dimension、Orientation、Engine、Theme、Reuse、New Resource、QA、Risk 和 Open Question | 尚不是 LLM Semantic Planner；Page Template 和 Reuse Scoring 覆盖有限；缺少 Typed Subtask |
| Theme | 基础可用 | 创建、激活、校验 Theme；Planner 读取 Theme Contract | 缺少 Structured Visual Token、Inheritance、Version 和 Conflict Resolution |
| Memory | 基础可用 | 记录 Decision、Lesson、Mistake、Best Practice；Context 递归加载 | 缺少 Retrieval、Relevance Ranking、Deduplication 和自动沉淀 |
| Resource Contract | 可用 | Manifest、Dimension、Format、Alpha、Naming、Target Engine 和 Import Hint | 缺少 Dependency、Variant、Atlas、Nine-slice 和 Reference Tracking |
| Asset QA | 可用 | 校验真实 Image Asset 的 Dimension、Format、Alpha 和 Naming | 缺少 Semantic、Art Consistency、Layout、Readability 和 Multi-resolution QA |
| Protected Editing | 可用 | Mask Composition 并验证非目标像素未变化 | 尚未进入 Runtime 自动修图循环 |
| Export | 基础可用 | Deterministic Validation、Copy、Report 和 Generic / Unity / Godot / Unreal Metadata | Sidecar 不等于 Native Engine Import；Export Agent 仍是 Contract |
| Runtime | 基础可用 | 创建或恢复 Task、解析 Workflow、Checkpoint Pipeline、保存 Failure、完成后持久化 | 缺少 Approval、Capability Discovery、Concurrency、Policy Retry 和 Cancel |
| Task | 基础可用 | Schema v2；Status、Current Agent、Resume Index、Event、Output、Error 和 Timestamp | 缺少严格 Agent Input / Output Contract、Schema Validation 和 Migration Tool |
| Task Store / Run History | 基础可用 | `task.json`、`context.json`、`events.jsonl`、`outputs.json`、失败时 `error.json` | 缺少 Run Diff、Replay、Retention、Search 和可视化审计 |
| Agent Interface | 基础可用 | Agent 接收并返回同一个 Task；Planner 执行真实工作；其余 Built-in Agent 保持解耦 | Director、Theme、Resource、Prompt、QA、Export 仍只记录 Contract Behavior |
| Context Loader | 基础可用 | 读取 Project Config、Current Theme、Project Workflow、Resource 和 Memory；Run 保存 Context Snapshot | 缺少 Historical Task、Tool Capability、Git Status、Source Provenance 和 Relevance Trimming |
| Prompt Builder | 未开发 | 只有 Prompt Agent Contract | 缺少 Model-neutral Prompt IR、Template Composition、Negative Constraint 和 Version Record |
| Generation / Editing | 未开发 | Runtime 尚未调用 Image Generation、Figma 或其他 Production Tool | 缺少 Provider / Tool Adapter、Artifact Registration 和 Revision Loop |
| Semantic QA | 未开发 | 无真实 Agent-level Semantic Check | 缺少 Theme、Composition、Content、UI Usability 和 Cross-page Consistency QA |
| ChatGPT Integration Contract | 未开发 | README 描述预期调用关系 | 缺少 Stable Machine Interface、Result Protocol 和 Host Guide |
| Git Change Management | 未开发 | Git 是原则，但 Runtime 不管理 Commit Lifecycle | 缺少 Change Set、Branch / Commit Strategy、Rollback 和 Human Approval |

#### 2.1 当前可以真实完成的闭环

```text
Project Init
-> 创建 Theme、Workflow 和 Resource Manifest
-> 自然语言 Requirement 进入 Runtime
-> Workflow 解析为 Pipeline
-> Planner 生成结构化 UI Production Plan
-> Task / Context / Event / Output 持久化
-> 可选 Asset Validation 与 Protected Edit
-> Engine Adapter Export
-> 生成 Deterministic Report
```

Planner 已经能够针对《韭菜派对》商店页需求输出 Canvas、Orientation、Target Engine、Theme Constraint、Resource Reuse Candidate、Missing Resource、QA Criteria、Risk 和 Open Question。

#### 2.2 当前尚不能完成的关键闭环

下面这句自然语言仍不能仅靠 GUIF 自动完成：

```text
“为 LeekParty 制作一个符合现有中世纪港口风格的商店页面，
复用已有金币和按钮，生成缺失资源，检查后导出 Unity。”
```

GUIF 现在能够自动完成其中的结构化规划，但 Director、Theme、Resource、Prompt、Generation、QA 和 Export Agent 尚未形成真实自动生产链，因此还不能自动生成视觉产物、判断视觉质量、循环修订并交付完整 Engine-ready Output。

### 3. GUIF 预期待开发的内容

开发顺序以“尽快验证真实可用闭环”为原则，而不是继续扩充空 Interface。

#### Phase 1：可审计、可恢复的 Runtime 基础

已完成基础版本：

- Task Schema v2 和明确 Lifecycle；
- Git-friendly Run Directory；
- Context、Event、Output 和 Error 持久化；
- Agent 前后 Checkpoint；
- Load、List、Resume；
- Workflow 与 Pipeline 统一；
- Project Workflow Override；
- Resume 时检查 Agent Order 是否发生变化。

仍待开发：

- Declarative Error / Retry Policy；
- Human Approval、Skip 和 Cancel；
- Runtime Capability Discovery；
- Run Migration、Diff 和 Replay。

#### Phase 2：真实 Planner + Director

Planner 已在 alpha.11 完成第一版：

- Page Type、Dimension、Orientation 和 Target Engine 检测；
- Theme Contract 提取；
- Existing Resource Reuse Scoring；
- Missing Resource Suggestion；
- Deliverable、QA Criteria、Dependency、Risk 和 Open Question；
- Plan Schema Validation；
- Plan 写入 Task State 与 Output Index。

仍待开发：

- Real Director Agent；
- Composition、Hierarchy 和 Cross-page Coherence Review；
- 更完整的 Requirement Clarification；
- Typed Page / Component / Subtask；
- Planner 与 Director 的冲突和人工确认机制。

**阶段验收标准**：针对《韭菜派对》商店页，稳定产出可执行 Plan，并由 Director 对布局、主题、资源复用和风险做结构化审阅。alpha.11 已完成 Planner 部分。

#### Phase 3：Context 与 Memory Retrieval

目标：只向 Agent 提供与当前 Task 相关的 Project Knowledge，而不是加载全部内容。

- Built-in 与 Project Workflow 的 Source Provenance；
- Memory Index、Relevance Retrieval、Priority 和 Deduplication；
- Historical Task 和 Approved Artifact Retrieval；
- Theme / Resource Reference Graph；
- Context Source List 和 Size Budget；
- Resume 时使用原 Snapshot 或显式 Refresh 的规则。

#### Phase 4：Model-neutral Prompt IR

目标：将 UI Plan 和 Project Constraint 转换为可版本化、可审阅、可适配不同 Provider 的 Prompt Intermediate Representation。

- Positive Requirement、Negative Constraint、Reference、Dimension 和 Output Contract；
- Provider Adapter；
- Prompt Version 和 Provenance；
- Prompt 与 Generated Artifact 的双向引用。

#### Phase 5：Generation / Editing Tool Adapter

目标：让 Runtime 能调用 Image Generation、Image Editing、Figma 或其他 Production Tool，并登记产物。

- Tool Capability Discovery；
- Input / Output Adapter；
- Artifact Store 和 Resource Manifest Link；
- Protected Edit Integration；
- Retry、Alternative 和 Human Approval。

#### Phase 6：Semantic QA 与 Revision Loop

目标：检查视觉结果是否符合 Project，而不仅是检查 Pixel 和 Format。

- Theme Consistency；
- Composition、Readability 和 UI Usability；
- Cross-page Consistency；
- Resource Contract Compliance；
- QA Finding -> Revision Task -> Recheck Loop。

#### Phase 7：Production Export 与 Host Integration

目标：让 ChatGPT / Agent Host 能稳定地启动、观察、暂停、恢复和解释 GUIF Run，并交付 Engine-ready Output。

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

- Rule-based Planner 能否作为 LLM Planner 的稳定 Fallback，而不是演变成难维护的 Keyword Collection；
- 一个 Mutable `Task` 是否足以承载所有 UI Production 类型，还是需要 Typed Subtask；
- Agent Granularity 应固定，还是允许 Project 定义；
- Workflow v2 是否足以承担 Pipeline Source of Truth，还是需要独立 Execution Policy；
- Project Workflow 变化后，失败 Run 应迁移、冻结旧 Workflow，还是拒绝 Resume；
- Prompt Builder 应是 Core Capability，还是 Plugin；
- ChatGPT 是否始终是主要 Host，还是需要独立 Service API；
- Context Snapshot 是否应保存完整内容、Hash，还是受控 Reference；
- Failure Retry 是否默认重新执行失败 Agent，还是要求 Agent 提供 Idempotency Contract；
- 何时引入 Database，而不是继续使用 Git-friendly File Store；
- 如何防止 Framework 变成拥有大量 Interface、但没有完整生产闭环的架构样板。

### 6. 迭代记录

#### `v1.0.0-alpha.9`

- 建立 Runtime、Task、Agent、Registry 和 Pipeline Contract；
- Built-in Agent 为 Contract-level Behavior；
- Context Loader 读取 Project Config、Theme、Workflow、Resource 和 Memory。

#### `v1.0.0-alpha.10`

- Task Schema 升级到 v2；
- 增加 Lifecycle、Current Agent、Resume Index 和 Structured Error；
- 新增 Task Store 和 Git-friendly Run Directory；
- Pipeline 在每个 Agent 前后保存 Checkpoint；
- Runtime 支持 Load、List 和 Resume；
- CLI 新增 `run-list`、`run-show`、`run-resume`。

#### `v1.0.0-alpha.11`

- Workflow schema v2 新增可执行 `agents`；
- Runtime Pipeline 改为由 Built-in 或 Project Workflow 解析生成；
- 保持 Workflow schema v1 兼容并从 `manager` 推导 Agent Order；
- Pipeline Metadata 写入 Task 便于审计；
- Workflow Agent Order 改变时拒绝不安全 Resume；
- 用 `StructuredPlannerAgent` 替换 Planner Contract；
- 新增 UI Production Plan schema、校验、Theme Constraint、Resource Reuse、Missing Resource、QA、Risk 和 Open Question；
- 新增 Workflow-driven Runtime 和 Planner Test；
- 下一重点调整为 Real Director Agent 与 Context / Memory Retrieval。

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
User
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> Context Loader / Retrieval
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
- inspectable and recoverable Task Runs;
- Git-backed long-term truth.

GUIF does not replace design tools or game engines, manage complete game code, train foundation models, or become a general-purpose Agent Framework.

### 2. Verified state at alpha.11

GUIF can initialize Projects, manage Themes and Resource Contracts, validate Image Assets, protect non-target pixels, export deterministic Engine Adapter metadata, persist and resume Runs, and execute Workflow-driven Pipelines.

Workflow schema v2 declares both human-readable `steps` and executable `agents`. Project Workflows override built-in Workflows. Schema v1 remains readable through a legacy Manager-to-Agent mapping.

The first real built-in Agent is now available. `StructuredPlannerAgent` creates a validated UI Production Plan containing page classification, canvas dimensions, orientation, target Engine, Theme constraints, Resource reuse candidates, missing Resource suggestions, deliverables, QA criteria, dependencies, risks, open questions, and a Context summary. The Plan is persisted in Task State and the Output index.

The principal limitation is now narrower: Planner performs real work, but Director, Theme, Resource, Prompt, QA, Export, and Generation remain Contract-only or unimplemented. GUIF still cannot complete automatic image production, semantic review, revision, and Engine-ready delivery from one natural-language request.

### 3. Expected development

1. Finish Runtime policies: approval, retry, cancel, capability discovery, migration, diff, and replay.
2. Implement the real Director and complete Planner / Director collaboration.
3. Add relevance-based Context and Memory retrieval.
4. Define a model-neutral Prompt IR.
5. Integrate Generation and Editing tools through Adapters.
6. Implement Semantic QA and Revision Loops.
7. Add stable Agent Host, native Engine, and Git change-management contracts.

The immediate acceptance target remains the LeekParty medieval-harbor shop page. Alpha.11 can now produce its structured Plan; the next target is a Director review that resolves composition, visual hierarchy, Theme coherence, reusable assets, and human approval points.

### 4. Iteration gate

A Feature should not be implemented unless it serves the product definition, belongs to the target architecture, closes a verified capability gap, advances an end-to-end loop, defines Tests and Failure Behavior, and updates all living documentation.

### 5. Main risks and open assumptions

Key unresolved questions include whether the rule-based Planner remains a maintainable deterministic fallback, Task typing, Agent granularity, Workflow policy boundaries, resume behavior after Workflow changes, Prompt Builder ownership, Host strategy, Context snapshot semantics, retry idempotency, file-store scalability, and the risk of accumulating interfaces without proving a usable production loop.

### 6. Iteration history

- `alpha.9`: Runtime Contract, shared Task, Agent Registry, static Pipelines, and Context loading.
- `alpha.10`: Task schema v2, persistent Run Store, Agent checkpoints, structured failures, load/list/resume APIs and CLI commands.
- `alpha.11`: Workflow schema v2, Workflow-driven Pipelines, Project overrides, safe-resume Agent-order checks, and the first real Structured Planner Agent with validated persisted UI Production Plans.
