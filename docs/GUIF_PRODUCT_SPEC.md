# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.10`  
> Last reviewed / 最近审阅: 2026-07-28

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅和后续迭代基线。它不是一次性 Roadmap，也不是宣传文案。

GUIF 每次发生下列变化时，本文件必须在同一个版本或同一个 Pull Request 中同步更新：

- 产品定位、边界或核心原则发生变化；
- 新增、替换或移除 Runtime、Task、Agent、Pipeline、Context、Memory、Resource、QA、Export 等核心能力；
- 某项能力从“Contract / 占位”升级为“可实际完成工作”；
- CLI、ChatGPT 接入方式、Project 目录或数据格式发生兼容性变化；
- 迭代优先级、已知风险或待验证假设发生变化。

一次 Release 只有在 Feature、Test、CI、英文 README、中文 README、Version Metadata 和本文件一致时才算完成。

### 1. GUIF 的预期

#### 1.1 一句话定义

GUIF 是一个以自然语言为主要入口、由 ChatGPT 或其他 Agent Host 调度、以 Git 和 Project File 作为长期事实来源、面向游戏 UI 生产全过程的可执行 AI 工作框架。

#### 1.2 预期用户体验

用户主要表达目标，而不是手工操作底层命令。例如：

```text
用户：为《韭菜派对》制作中世纪港口商店页面。

ChatGPT / Agent Host
  -> 选择 Project
  -> 调用 GUIF Runtime
  -> 读取 Theme、Workflow、Resource、Memory 和历史 Run
  -> 生成结构化计划
  -> 复用已有资源并创建缺失资源
  -> 调用合适的 Model 或 Tool
  -> 自动 QA、修订和 Export
  -> 保存 Task、Output、Decision 和 Git Change
  -> 返回可审阅结果
```

CLI 保留用于开发、调试、自动化和 CI，但不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户描述目标，Framework 负责拆解和执行。
- **长期 Project Knowledge**：Theme、Decision、Lesson、Mistake 和 Best Practice 进入 Project 并由 Git 追踪。
- **可执行而非 Prompt Collection**：GUIF 必须产生结构化 Task、文件、报告、Resource 和可验证结果。
- **Model Agnostic**：Runtime 不直接依赖单一模型或 Provider。
- **Project Isolation**：Framework Code 与具体游戏 Project 分离，不同 Project 的知识和资源互不污染。
- **Deterministic Production**：Naming、Dimension、Alpha、Export、Validation 和 Engine Adaptation 尽可能可重复。
- **可审计、可恢复**：每个 Run 应能回答读取了什么、执行到哪里、为什么失败、产生了什么，以及如何继续。

#### 1.4 目标架构

```text
User
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> Context Loader
       -> Task Store
       -> Pipeline Selector
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
- **Runtime**：加载 Context、创建或恢复 Task、选择 Pipeline、调度 Agent、保存 Checkpoint 和处理失败；不包含具体美术业务逻辑。
- **Task Store**：持久化 Task Snapshot、Context Snapshot、Event、Output 和 Error。
- **Agent**：完成单一职责；Agent 不直接调用其他 Agent。
- **Pipeline**：声明 Agent 组合和执行顺序，并定义恢复位置。
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

以下结论基于 `v1.0.0-alpha.10` 仓库代码。

状态定义：

- **可用**：已经能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：目标明确，但仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化隔离目录和 `project.json`；新 Project 包含 `runs/` | Migration、Template、Archive 和 Schema Upgrade |
| Requirement Routing / Plan | 基础可用 | Keyword Routing 并生成 Plan JSON | 不是 Semantic Planning；无 Dependency Graph 和完整 Resource List |
| Workflow | 基础可用 | 加载和校验 Built-in / Project Workflow Manifest | Runtime 默认 Pipeline 与 Workflow 尚未统一 |
| Theme | 基础可用 | 创建、激活、校验 Theme；Context 读取 Current Theme | 缺少 Structured Visual Token、Inheritance、Version 和 Conflict Resolution |
| Memory | 基础可用 | 记录 Decision、Lesson、Mistake、Best Practice；Context 递归加载 | 缺少 Retrieval、Relevance Ranking、Deduplication 和自动沉淀 |
| Resource Contract | 可用 | Manifest、Dimension、Format、Alpha、Naming、Target Engine 和 Import Hint | 缺少 Dependency、Variant、Atlas、Nine-slice 和 Reference Tracking |
| Asset QA | 可用 | 校验真实图片的 Dimension、Format、Alpha 和 Naming | 缺少 Semantic、Art Consistency、Layout、Readability 和 Multi-resolution QA |
| Protected Editing | 可用 | Mask Composition 并验证非目标像素未变化 | 尚未进入 Runtime 自动修图循环 |
| Export | 基础可用 | Deterministic Validation、Copy、Report 和 Generic / Unity / Godot / Unreal Metadata | Sidecar 不等于 Native Engine Import |
| Runtime | 基础可用 | 创建或恢复 Task、Checkpoint Pipeline、保存 Failure、完成后持久化 | 缺少 Condition Branch、Policy Retry、Approval Gate、Concurrency 和 Capability Discovery |
| Task | 基础可用 | Schema v2；Status、Current Agent、Resume Index、Event、Output、Error 和 Timestamp | 缺少严格 Input / Output Contract、Schema Validation 和 Migration Tool |
| Task Store / Run History | 基础可用 | `task.json`、`context.json`、`events.jsonl`、`outputs.json`、失败时 `error.json` | 缺少 Run Diff、Replay、Retention、Search 和可视化审计 |
| Agent Interface | Contract 完成 | Agent 接收并返回同一个 Task；Agent 间解耦 | Built-in Agent 仍只记录 `contract-ready`，不执行真实工作 |
| Pipeline | Contract 完成 | 三条静态 Pipeline；Agent 前后保存 Checkpoint；支持从 Index 恢复 | 缺少 Declarative Config、Condition、Loop、Error Policy 和 Project Override |
| Context Loader | 基础可用 | 读取 Project Config、Current Theme、Project Workflow、Resource 和 Memory；Run 保存 Context Snapshot | 缺少 Built-in Workflow、历史 Task、Tool Capability、Git Status 和 Relevance Trimming |
| Prompt Builder | 未开发 | 只有 Prompt Agent Contract | 缺少 Model-neutral Prompt IR、Template Composition、Negative Constraint 和 Version Record |
| Generation / Editing | 未开发 | Runtime 尚未调用 Image Generation、Figma 或其他 Production Tool | 缺少 Provider / Tool Adapter、Artifact Registration 和 Revision Loop |
| Semantic QA | 未开发 | 无真实 Agent-level Semantic Check | 缺少 Theme、Composition、Content、UI Usability 和 Cross-page Consistency QA |
| ChatGPT Integration Contract | 未开发 | README 描述预期调用关系 | 缺少 Stable Machine Interface、Result Protocol 和 Host Guide |
| Git Change Management | 未开发 | Git 是原则，但 Runtime 不管理 Commit Lifecycle | 缺少 Change Set、Branch / Commit Strategy、Rollback 和 Human Approval |

#### 2.1 当前可以真实完成的闭环

```text
Project Init
-> 手工或 CLI 创建 Theme、Workflow、Resource Manifest
-> 运行 Contract Pipeline 并持久化 Task Run
-> 校验 Image Asset
-> 可选 Protected Edit
-> Engine Adapter Export
-> 生成 Deterministic Report
```

Runtime Run 现在可以保存、查看和在 Agent Failure 后从失败位置重新执行。

#### 2.2 当前尚不能完成的关键闭环

下面这句自然语言仍不能仅靠 GUIF 自动完成：

```text
“为 LeekParty 制作一个符合现有中世纪港口风格的商店页面，
复用已有金币和按钮，生成缺失资源，检查后导出 Unity。”
```

原因是 Planner、Director、Theme、Resource、Prompt、QA 和 Export Agent 仍主要是 Contract Agent。GUIF 尚不能自动形成真实计划、调用生成工具、判断视觉质量、循环修订并提交完整产物。

### 3. GUIF 预期待开发的内容

开发顺序以“尽快验证真实可用闭环”为原则，而不是继续扩充空 Interface。

#### Phase 1：可审计、可恢复的 Runtime 基础

目标：每次自然语言执行都形成可保存、可检查和可恢复的 Run。

已在 alpha.10 完成：

- Task Schema v2 和明确 Lifecycle Status；
- `runs/<task-id>/task.json`；
- Context Snapshot、Event Log、Output Index 和 Error Report；
- Agent 前后 Checkpoint；
- Failure Position 保存；
- `run-list`、`run-show` 和 `run-resume`；
- 已完成 Task 禁止 Resume。

仍待开发：

- Pipeline 与 Workflow Manifest 统一；
- Declarative Error / Retry Policy；
- Human Approval、Skip 和 Cancel；
- Runtime Capability Discovery；
- Run Migration、Diff 和 Replay。

**阶段验收标准**：Task 可保存、退出、重新加载并继续执行；用户能看到每一步的状态、Output 和 Failure Reason。alpha.10 已完成基础版本，但尚未达到完整 Policy 和 Migration 能力。

#### Phase 2：真实 Planner + Director

目标：把一句需求转换成可由后续 Agent 消费的结构化 UI Production Plan，而不是 Keyword Routing。

- Requirement Clarification Rule；
- Page、Component、Resource、Constraint 和 Deliverable 拆分；
- Dependency 和 Execution Order；
- Existing Asset Reuse Analysis；
- Risk、Unknown 和 Human Confirmation Point；
- Plan 写入 Task Output，并具有稳定 Schema。

**验收标准**：针对《韭菜派对》商店页，稳定产出 Page Structure、Reusable Resource、New Resource、Dimension、Format、QA 和 Export Target 的结构化 Plan。

#### Phase 3：Context 与 Memory Retrieval

目标：只向 Agent 提供与当前 Task 相关的 Project Knowledge，而不是加载所有内容。

- Built-in 与 Project Workflow 统一解析；
- Memory Index、Relevance Retrieval、Priority 和 Deduplication；
- Historical Task 和 Approved Artifact Retrieval；
- Theme / Resource Reference Graph；
- Context Source List 和 Size Budget。

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

- 一个 Mutable `Task` 是否足以承载所有 UI Production 类型，还是需要 Typed Subtask；
- Agent Granularity 应固定，还是允许 Project 定义；
- Pipeline 和 Workflow 应完全合并，还是保留 Runtime / Domain 两层；
- Prompt Builder 应是 Core Capability，还是 Plugin；
- ChatGPT 是否始终是主要 Host，还是需要独立 Service API；
- Context Snapshot 是否应保存完整内容、Hash，还是受控 Reference；
- Resume 时应使用原 Context Snapshot，还是允许显式 Refresh；
- Failure Retry 是否默认重新执行失败 Agent，还是要求 Agent 提供 Idempotency Contract；
- 何时引入 Database，而不是继续使用 Git-friendly File Store；
- 如何防止 Framework 变成拥有大量 Interface、但没有完整生产闭环的“架构样板”。

### 6. 迭代记录

#### `v1.0.0-alpha.9`

- 建立 Runtime、Task、Agent、Registry 和 Pipeline Contract；
- Built-in Agent 仍为 Contract-level Behavior；
- Context Loader 读取 Project Config、Theme、Workflow、Resource 和 Memory。

#### `v1.0.0-alpha.10`

- Task Schema 升级到 v2；
- 增加 `pending`、`running`、`failed`、`completed` Lifecycle；
- 增加 Current Agent、Resume Index 和 Structured Error；
- 新增 Task Store 和 Git-friendly Run Directory；
- Pipeline 在每个 Agent 前后保存 Checkpoint；
- Runtime 支持 Load、List 和 Resume；
- CLI 新增 `run-list`、`run-show`、`run-resume`；
- 增加 Failure / Resume Test；
- 下一重点调整为 Real Planner 和 Pipeline / Workflow Unification。

---

## English Version

### 0. Purpose and maintenance rule

This file is GUIF's product definition, verified capability review, and iteration baseline. It is a living specification, not a one-time roadmap or marketing document.

It must be updated in the same release or pull request whenever product scope, architecture, core capability status, compatibility, priorities, risks, or open assumptions change.

A release is complete only when feature, tests, CI, both READMEs, version metadata, and this specification agree.

### 1. Expected product

GUIF is an executable AI work framework for end-to-end game UI production. Natural language is the primary interface, ChatGPT or another Agent Host performs conversational orchestration, and Git plus project files remain the long-term source of truth.

Expected flow:

```text
User
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> Context Loader
       -> Task Store
       -> Pipeline Selector
       -> Agent Registry
       -> Outputs, Reports, Memory, and Git Changes
```

Core principles:

- natural-language first;
- executable results rather than a prompt collection;
- model-agnostic Runtime orchestration;
- isolated project knowledge;
- deterministic production contracts;
- inspectable and recoverable task runs;
- Git-backed long-term truth.

GUIF does not replace design tools or game engines, manage complete game code, train foundation models, or become a general-purpose agent framework.

### 2. Verified state at alpha.10

GUIF can initialize projects, manage themes and resource contracts, validate image assets, protect non-target pixels, export deterministic engine-adapter metadata, and execute contract pipelines.

Alpha.10 adds persisted and resumable Task runs:

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  error.json  # only while failed
```

Task schema v2 contains lifecycle status, current Agent, next Agent index, events, outputs, structured failure data, and timestamps. Pipelines checkpoint before and after every Agent. Runtime can list, load, and resume an incomplete run.

The principal limitation remains unchanged: built-in Agents are still contract-only. GUIF does not yet perform semantic planning, image generation, visual QA, automatic revision, or a complete natural-language production loop.

### 3. Expected development

1. Finish auditable Runtime foundations: unify Pipeline and Workflow, add policies, approval gates, capability discovery, migration, diff, and replay.
2. Implement a real structured Planner and Director.
3. Add relevant Context and Memory retrieval.
4. Define a model-neutral Prompt IR.
5. Integrate generation and editing tools through adapters.
6. Implement semantic QA and revision loops.
7. Add stable Agent Host, native engine, and Git change-management contracts.

The immediate acceptance target is the LeekParty medieval-harbor shop page: GUIF must turn one natural-language request into a structured plan describing page composition, reusable assets, new assets, dimensions, formats, QA, and export targets.

### 4. Iteration gate

A feature should not be implemented unless it serves the product definition, belongs to the target architecture, closes a verified capability gap, advances an end-to-end loop, defines tests and failure behavior, and updates all living documentation.

### 5. Main risks and open assumptions

Key unresolved questions include Task typing, Agent granularity, Pipeline versus Workflow layering, Prompt Builder ownership, Host strategy, Context snapshot semantics, retry idempotency, file-store scalability, and the risk of accumulating interfaces without proving a usable production loop.

### 6. Iteration history

- `alpha.9`: Runtime Contract, shared Task, Agent Registry, static Pipelines, and Context loading.
- `alpha.10`: Task schema v2, persistent Run Store, Agent checkpoints, structured failures, load/list/resume APIs and CLI commands, and failure-resume tests.
