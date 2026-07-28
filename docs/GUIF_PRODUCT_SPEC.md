# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.9`  
> Last reviewed / 最近审阅: 2026-07-28

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅和后续迭代基线。它不是一次性 Roadmap，也不是宣传文案。

GUIF 每次发生下列变化时，本文件必须在同一个版本或同一个 Pull Request 中同步更新：

- 产品定位、边界或核心原则发生变化；
- 新增、替换或移除 Runtime、Agent、Pipeline、Context、Memory、Resource、QA、Export 等核心能力；
- 某项能力从“契约/占位”升级为“可实际完成工作”；
- CLI、ChatGPT 接入方式、项目目录或数据格式发生兼容性变化；
- 迭代优先级、已知风险或待验证假设发生变化。

版本发布只有在代码、测试、CI、README、版本号和本文件一致时才算完成。

### 1. GUIF 的预期

#### 1.1 一句话定义

GUIF 是一个以自然语言为主要入口、由 ChatGPT 或其他 Agent Host 调度、以 Git 和项目文件作为长期事实来源、面向游戏 UI 生产全过程的可执行 AI 工作框架。

#### 1.2 预期用户体验

用户主要表达需求，而不是操作底层命令。例如：

```text
用户：为《韭菜派对》制作中世纪港口商店页面。

ChatGPT / Agent Host：
1. 选择项目；
2. 调用 GUIF Runtime；
3. 读取主题、工作流、资源、历史决策和规则；
4. 生成并执行任务计划；
5. 复用已有资源，创建缺失资源；
6. 调用适合的模型或工具；
7. 自动 QA、修订、导出并记录结果；
8. 将可审阅的产物和变更返回给用户。
```

CLI 仍然保留，但主要服务于开发、调试、自动化和 CI，不应成为普通用户的主要工作方式。

#### 1.3 核心价值

- **自然语言优先**：用户描述目标，框架负责拆解和执行。
- **长期项目记忆**：主题、决策、经验、错误和最佳实践存入项目，并由 Git 追踪。
- **可执行而非提示词集合**：GUIF 必须产生结构化 Task、文件、报告、资源和可验证结果。
- **模型无关**：Runtime 不直接依赖 OpenAI、Claude、Gemini 或其他单一模型。
- **项目隔离**：框架代码与具体游戏项目分离，各项目的知识、资源和历史互不污染。
- **确定性生产环节**：命名、尺寸、Alpha、导出、校验和引擎适配尽可能可重复。
- **可审计**：每个任务应能回答“读取了什么、做了什么、为什么这样做、产生了什么”。

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

- **Agent Host**：理解对话、确认用户意图、调用 GUIF、向用户解释结果。
- **Runtime**：加载上下文、创建 Task、选择 Pipeline、调度 Agent、处理生命周期和失败恢复；不包含具体美术业务逻辑。
- **Agent**：完成单一职责；Agent 不直接调用其他 Agent。
- **Pipeline**：声明 Agent 的组合和执行顺序。
- **Task**：贯穿整个执行过程的统一状态、事件、输入和输出载体。
- **Context**：项目配置、主题、工作流、资源、记忆、历史运行和环境能力的只读快照或受控引用。
- **Git**：长期事实来源、变更记录和协作边界。

#### 1.5 非目标

GUIF 不计划：

- 替代 Photoshop、Figma、Unity、Godot 或 Unreal；
- 管理完整游戏逻辑、服务器、数值或关卡代码；
- 训练基础模型；
- 成为通用的任意行业 Agent 框架；
- 将所有 AI 和工具逻辑塞进 Runtime；
- 用不可追踪的聊天记忆替代项目文件和 Git。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.9` 仓库代码。状态定义：

- **可用**：已经能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **契约完成**：接口和执行骨架存在，尚未完成真实业务；
- **未开发**：目标明确，但仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project | 可用 | 初始化项目目录和 `project.json`；项目隔离 | 项目迁移、模板、归档和版本升级机制 |
| Requirement Routing / Plan | 基础可用 | 关键词路由到工作流并生成计划 JSON | 不是语义规划；不会形成可执行依赖图或资源清单 |
| Workflow | 基础可用 | 可加载、校验内置和项目工作流 Manifest | Runtime 默认 Pipeline 与项目 Workflow 尚未统一 |
| Theme | 基础可用 | 创建、激活、校验主题文件；Context 可读取当前主题 | 缺少结构化视觉令牌、继承、版本和冲突处理 |
| Memory | 基础可用 | 可记录 decision、lesson、mistake、best-practice；Runtime 递归加载 | 缺少检索、相关性排序、去重、生命周期和自动沉淀 |
| Resource Contract | 可用 | 资源 Manifest、尺寸、格式、Alpha、命名、目标引擎和导入提示 | 缺少资源关系、变体、图集、九宫格和引用追踪 |
| Asset QA | 可用 | 校验真实图片的尺寸、格式、Alpha 和命名 | 缺少语义、美术一致性、布局、可读性和多分辨率 QA |
| Protected Editing | 可用 | 遮罩合成并验证非目标像素未变化 | 尚未接入 Runtime 自动修图循环 |
| Export | 基础可用 | 确定性校验、复制、报告和通用/Unity/Godot/Unreal 适配元数据 | 适配结果仍是 GUIF sidecar，不等于原生引擎导入 |
| Runtime | 契约完成 | 加载 Context、创建 Task、选择 Pipeline、通过 Registry 顺序执行 Agent | 无持久化运行、暂停恢复、重试、并发、条件分支和能力发现 |
| Task | 契约完成 | 统一承载 requirement、context、state、events 和 outputs | 缺少 Schema 版本、输入输出契约、状态机、持久化和可恢复性 |
| Agent Interface | 契约完成 | 所有 Agent 接收并返回同一 Task；Agent 间解耦 | 内置 Agent 目前只记录 `contract-ready`，不执行真实工作 |
| Pipeline | 契约完成 | `ui-production`、`planning`、`resource-production` 静态流水线 | 缺少声明式配置、条件节点、回路、错误策略和项目覆盖 |
| Context Loader | 基础可用 | 读取项目配置、当前主题、项目 Workflow、Resource 和 Memory | 缺少内置工作流、历史 Task、工具能力、Git 状态和相关性裁剪 |
| Prompt Builder | 未开发 | 只有 Prompt Agent 契约描述 | 缺少模型中立 Prompt IR、模板组合、负面约束和版本记录 |
| Generation / Editing | 未开发 | Runtime 尚未调用图片生成、Figma 或其他生产工具 | 缺少 Provider/Tool Adapter、产物登记和修订循环 |
| Semantic QA | 未开发 | 无真实 Agent 级语义检查 | 缺少视觉主题、构图、内容、UI 可用性和跨页面一致性检查 |
| Task Persistence / Run History | 未开发 | `guif run` 返回 Task，但未形成稳定运行记录 | 无 run manifest、恢复、重放、差异比较和审计页面 |
| ChatGPT Integration Contract | 未开发 | README 描述了预期调用关系 | 缺少稳定的机器接口、输出协议和 Host 使用说明 |
| Git Change Management | 未开发 | Git 是原则，但 Runtime 不管理提交生命周期 | 缺少变更集、分支/提交策略、回滚和人工审批点 |

#### 2.1 当前可以真实完成的闭环

当前最完整的闭环是：

```text
项目初始化
-> 手工/CLI 创建主题、工作流或资源 Manifest
-> 校验图片资源
-> 可选的保护像素编辑
-> 通过引擎 Adapter 导出
-> 生成确定性报告
```

#### 2.2 当前尚不能完成的关键闭环

下面这句自然语言目前不能仅靠 GUIF 自动完成：

```text
“为 LeekParty 制作一个符合现有中世纪港口风格的商店页面，复用已有金币和按钮，生成缺失资源，检查后导出 Unity。”
```

原因是 Planner、Director、Theme、Resource、Prompt、QA、Export 在 Runtime 中仍主要是契约 Agent；GUIF 尚不能自动生成真实计划、调用生成工具、评价视觉结果、循环修订并提交完整产物。

### 3. GUIF 预期待开发的内容

开发顺序应以“尽快验证真实可用闭环”为原则，而不是继续扩充空接口。

#### Phase 1：可审计的 Runtime 基础

目标：每次自然语言执行都形成可保存、可检查、可恢复的运行记录。

- Task Schema 版本和严格输入输出结构；
- `runs/<run-id>/task.json`、事件日志、产物索引和错误报告；
- Agent 失败、跳过、重试、人工确认和恢复机制；
- Context 快照及来源清单；
- Pipeline 和 Workflow 的关系统一；
- Runtime 能力发现，明确当前 Host 可调用的工具和 Provider。

**验收标准**：同一 Task 可以保存、退出、重新加载和继续执行；用户能看到每一步的输入、结果和失败原因。

#### Phase 2：真实 Planner + Director

目标：将一句需求转换成可执行 UI 生产计划，而不是关键词路由。

- 需求澄清规则；
- 页面、组件、资源、约束和交付物拆分；
- 依赖关系和执行顺序；
- 已有资源复用分析；
- 风险、未知项和人工确认点；
- 计划结果写入 Task，并可由后续 Agent 消费。

**验收标准**：针对《韭菜派对》商店页，能稳定产出包含页面构成、复用资源、新建资源、尺寸、格式、QA 和导出目标的结构化计划。

#### Phase 3：Context 与 Memory 检索

目标：不是把全部文件塞给 Agent，而是选择与当前任务相关的项目知识。

- 统一读取内置与项目 Workflow；
- Memory 索引、相关性检索、优先级和去重；
- 历史 Task 和已批准产物检索；
- 主题和资源引用关系；
- 上下文预算和裁剪报告；
- 决策、经验与事实的不同可信度等级。

**验收标准**：修改商店人物时，自动检索到此前“人物靠左、暖金黄昏、去噪点、避免海盗元素”等相关规则，而不是加载所有无关记录。

#### Phase 4：Prompt IR 与 Provider Adapter

目标：建立模型无关的生成说明，而不是把 GUIF 绑定到某一种提示词格式。

- Prompt Intermediate Representation；
- 主题、资源、布局、历史决定和负面约束的组合；
- Provider Adapter，将 Prompt IR 转为具体模型调用；
- Prompt 版本、来源和结果关联；
- 文本模型、图片模型和编辑工具使用统一的能力接口。

**验收标准**：同一 Task 可以使用不同 Provider 执行，而 Runtime、Task 和项目数据结构不需要变化。

#### Phase 5：真实资源生产与修订循环

目标：从计划生成或编辑实际资源，并将其登记到项目中。

- Generation / Editing Agent；
- 生成资源、效果图和生产资源的分离；
- Manifest 自动创建和更新；
- 局部修改与 protected editing 集成；
- 修订版本、父子关系和批准状态；
- 失败后的自动或人工修订循环。

**验收标准**：用户说“人物往左一点”时，GUIF 能找到上一次批准的图和对应资源，仅修改目标区域，保留其他像素并记录新版本。

#### Phase 6：多层 QA

目标：将现有技术 QA 扩展为完整 UI 生产 QA。

- 文件、尺寸、Alpha、命名等技术 QA；
- 主题、角色、光照和噪点等视觉一致性 QA；
- 布局、遮挡、文字可读性和安全区 QA；
- 跨页面、跨资源一致性；
- 可配置通过阈值和人工审批门；
- QA 失败自动形成可执行修订建议。

**验收标准**：QA 报告不仅写“失败”，还指出违反了哪条项目规则、位于哪个产物、建议如何修复。

#### Phase 7：导出、Git 与交付闭环

目标：将批准资源可靠地交付给游戏项目，并完整记录变更。

- 增量导出、校验和和未变资源跳过；
- 图集、九宫格、字体、动画等资源类型；
- 更接近原生引擎的导入适配；
- 变更集、Git diff、提交消息和审批点；
- 可回滚交付；
- 任务完成报告与 Memory 自动沉淀。

**验收标准**：完成任务后，用户得到清楚的产物、QA、导出和 Git 变更摘要，并能安全回滚。

#### Phase 8：ChatGPT / Agent Host 正式接入

目标：让自然语言成为真正稳定的主要入口。

- 明确 Runtime API/CLI 的机器可读协议；
- Host 调用指南和错误处理规范；
- 用户确认、权限和高风险变更边界；
- 多轮对话与同一 Task 的关联；
- ChatGPT 中的项目选择、进度汇报和结果呈现约定。

**验收标准**：用户无需了解 GUIF 命令即可完成一项真实 UI 工作；CLI 仅作为后台执行和调试接口。

### 4. 开发决策门槛

任何新功能开发前必须回答：

1. 它是否直接服务“自然语言驱动的游戏 UI 生产闭环”？
2. 它属于目标架构中的哪个职责？
3. 它会替代真实缺口，还是只增加新的空接口？
4. 是否有《韭菜派对》或另一个实际项目的验收场景？
5. 是否可以通过 Task、产物或报告验证结果？
6. 是否会破坏模型无关、项目隔离或 Git 可审计原则？
7. 本文档的“当前状态”和“后续阶段”是否同步更新？

无法明确回答时，默认不开发。

### 5. 关键风险

- **框架先行过度**：接口不断增加，但没有真实 Agent 完成工作。
- **ChatGPT 与 GUIF 脱节**：CLI 能运行，但 Host 不知道如何可靠调用和解释结果。
- **上下文堆积**：全部加载导致成本高、冲突多、结果不稳定。
- **Task 成为无结构字典**：后期难以恢复、迁移和验证。
- **重复的 Workflow/Pipeline 抽象**：两套概念并存造成路由和执行不一致。
- **把模型细节写入核心**：失去 AI-agnostic 能力。
- **文档领先于实现**：README 或规格声称的能力超过代码事实。

### 6. 待验证假设

- 一个统一 Task 是否足以覆盖页面设计、单资源制作、局部修图和批量导出；
- Agent 粒度是否固定，还是允许项目定义自己的 Agent；
- Pipeline 与 Workflow 是否最终合并为一个概念；
- Prompt Builder 应作为核心 Agent 还是插件；
- ChatGPT 是否是默认 Host，但不成为技术依赖；
- Memory 应以文件检索为主，还是需要数据库/向量索引；
- 视觉 QA 可以自动达到什么程度，哪些节点必须人工批准；
- GUIF 是否只管理 UI 产物，还是还管理 Figma/引擎中的布局实现。

这些假设必须通过真实项目任务验证，不能仅通过架构讨论定案。

### 7. 下一迭代建议

在继续增加图片、Figma 或 GitHub Agent 前，优先完成：

1. Task 持久化和 Run Manifest；
2. Pipeline/Workflow 统一设计；
3. 第一个真实 Planner Agent；
4. 用《韭菜派对》“中世纪港口商店页”作为端到端验收案例。

这四项完成后，GUIF 才从“可执行的框架契约”迈向“能完成第一项真实工作的框架”。

---

## English Version

### 0. Purpose and Maintenance Policy

This file is GUIF's product definition, current-state review, and evolution baseline. It is a living specification, not a one-off roadmap or marketing document.

This file must be updated in the same release or pull request whenever any of the following changes:

- product positioning, scope, or core principles;
- core Runtime, Agent, Pipeline, Context, Memory, Resource, QA, or Export behavior;
- a capability moves from contract/placeholder status to real production behavior;
- CLI, ChatGPT integration, project layout, or data formats change incompatibly;
- priorities, known risks, or open assumptions change.

A release is complete only when code, tests, CI, README, version metadata, and this specification agree.

### 1. Expected GUIF

#### 1.1 One-sentence definition

GUIF is an executable AI work framework for end-to-end game UI production, using natural language as the primary interface, ChatGPT or another agent host as the orchestrator, and Git-backed project files as the durable source of truth.

#### 1.2 Expected user experience

The user expresses an outcome instead of operating low-level commands:

```text
User: Create a medieval harbor shop page for LeekParty.

ChatGPT / Agent Host:
1. selects the project;
2. invokes GUIF Runtime;
3. loads theme, workflows, resources, decisions, history, and rules;
4. creates and executes a task plan;
5. reuses existing assets and creates missing ones;
6. invokes appropriate models or tools;
7. performs QA, revision, export, and recording;
8. returns reviewable outputs and changes to the user.
```

The CLI remains available for development, debugging, automation, and CI, but it should not be the normal user's primary workflow.

#### 1.3 Core value

- **Natural-language first**: users state goals; the framework decomposes and executes them.
- **Durable project knowledge**: themes, decisions, lessons, mistakes, and best practices live in project files tracked by Git.
- **Executable, not a prompt collection**: GUIF must produce structured tasks, files, reports, assets, and verifiable results.
- **Model-agnostic**: Runtime does not directly depend on one model provider.
- **Project isolation**: framework code and game projects remain separate; project knowledge does not leak across projects.
- **Deterministic production stages**: naming, dimensions, alpha, export, validation, and engine adaptation should be reproducible where possible.
- **Auditable**: every run should explain what it loaded, what it did, why, and what it produced.

#### 1.4 Target architecture

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

Responsibilities:

- **Agent Host** understands conversation, confirms intent, invokes GUIF, and presents results.
- **Runtime** loads context, creates tasks, selects pipelines, schedules agents, and manages lifecycle and recovery; it contains no art-domain business logic.
- **Agent** performs one responsibility; agents do not directly invoke one another.
- **Pipeline** declares agent composition and order.
- **Task** is the shared carrier for state, events, inputs, and outputs throughout a run.
- **Context** is a read-only snapshot or controlled reference to project configuration, themes, workflows, resources, memory, run history, and environment capabilities.
- **Git** is the durable source of truth, change history, and collaboration boundary.

#### 1.5 Non-goals

GUIF does not aim to:

- replace Photoshop, Figma, Unity, Godot, or Unreal;
- manage an entire game's logic, backend, balance, or level code;
- train foundation models;
- become a generic agent framework for every industry;
- place all AI and tool behavior inside Runtime;
- replace Git-backed project knowledge with opaque chat memory.

### 2. Current GUIF Content and Progress

The following review is based on repository state at `v1.0.0-alpha.9`.

Status definitions:

- **Usable**: performs explicit, verifiable work;
- **Foundation usable**: the main implementation exists but coverage or automation remains limited;
- **Contract complete**: executable interface and skeleton exist, but real domain work is not implemented;
- **Not implemented**: target is known but no usable implementation exists.

| Capability | Status | What exists now | Main gap |
|---|---|---|---|
| Project | Usable | Project layout and `project.json` initialization; project isolation | Migration, templates, archive, and schema upgrade support |
| Requirement Routing / Plan | Foundation usable | Keyword routing to workflow and plan JSON creation | No semantic planning, dependency graph, or asset breakdown |
| Workflow | Foundation usable | Built-in/project workflow loading and validation | Runtime Pipeline and project Workflow are not yet unified |
| Theme | Foundation usable | Theme creation, activation, validation, and Runtime loading | Structured visual tokens, inheritance, versioning, and conflict resolution |
| Memory | Foundation usable | Decision, lesson, mistake, and best-practice records; recursive Runtime loading | Retrieval, relevance, deduplication, lifecycle, and automatic learning |
| Resource Contract | Usable | Manifests for size, format, alpha, naming, target engine, and import hints | Relationships, variants, atlases, nine-slice, and reference tracking |
| Asset QA | Usable | Real image checks for dimensions, format, alpha, and naming | Semantic, art consistency, layout, readability, and multi-resolution QA |
| Protected Editing | Usable | Mask composition and verification that protected pixels remain unchanged | Not integrated into a Runtime revision loop |
| Export | Foundation usable | Deterministic validation, staging, reporting, and generic/Unity/Godot/Unreal adapter metadata | Adapter output is GUIF sidecar metadata, not native engine import |
| Runtime | Contract complete | Context loading, Task creation, Pipeline selection, Registry-based sequential execution | Persistence, pause/resume, retries, concurrency, branches, and capability discovery |
| Task | Contract complete | Shared requirement, context, state, events, and outputs | Schema versioning, typed I/O, state machine, persistence, and recovery |
| Agent Interface | Contract complete | Agents receive and return the same Task and remain decoupled | Built-ins only record `contract-ready`; they do not perform real work |
| Pipeline | Contract complete | Static `ui-production`, `planning`, and `resource-production` pipelines | Declarative config, conditions, loops, error policy, and project overrides |
| Context Loader | Foundation usable | Project config, active theme, project workflows, resources, and memory | Built-in workflows, run history, tool capability, Git state, and relevance selection |
| Prompt Builder | Not implemented | Prompt Agent responsibility exists as a contract | Model-neutral Prompt IR, composition, negative constraints, and version records |
| Generation / Editing | Not implemented | No image-generation, Figma, or production tool invocation from Runtime | Provider/tool adapters, artifact registration, and revision loop |
| Semantic QA | Not implemented | No real agent-level semantic review | Theme, composition, content, usability, and cross-page consistency checks |
| Task Persistence / Run History | Not implemented | `guif run` returns a Task but no durable run record | Run manifest, resume, replay, diff, and audit view |
| ChatGPT Integration Contract | Not implemented | README describes the intended relationship | Stable machine interface, output protocol, and host guide |
| Git Change Management | Not implemented | Git is a principle, but Runtime does not manage commits | Change sets, branch/commit policy, rollback, and approval gates |

#### 2.1 Current real closed loop

The most complete current loop is:

```text
Project initialization
-> manual/CLI theme, workflow, or resource manifest creation
-> image asset validation
-> optional protected-pixel editing
-> export through an engine adapter
-> deterministic report
```

#### 2.2 Critical loop not yet available

GUIF cannot yet autonomously complete this request:

```text
“Create a shop page for LeekParty that follows the existing medieval harbor style, reuse the current coin and button assets, generate missing assets, review them, and export to Unity.”
```

Planner, Director, Theme, Resource, Prompt, QA, and Export are still primarily contract agents inside Runtime. GUIF does not yet create a real production plan, invoke generation tools, judge visual results, iterate revisions, and commit a complete deliverable.

### 3. Expected Development

Development order should prioritize the earliest real end-to-end validation, not additional empty interfaces.

#### Phase 1: Auditable Runtime Foundation

Goal: every natural-language run creates a durable, inspectable, and recoverable record.

- versioned Task schema and typed input/output;
- `runs/<run-id>/task.json`, event log, artifact index, and error report;
- failure, skip, retry, human approval, and resume behavior;
- context snapshot and source inventory;
- unified Pipeline/Workflow model;
- runtime capability discovery for available tools and providers.

**Acceptance**: a Task can be saved, exited, reloaded, and continued; the user can inspect inputs, outputs, and failure reasons for every step.

#### Phase 2: Real Planner + Director

Goal: transform one requirement into an executable UI production plan instead of keyword routing.

- clarification rules;
- page, component, asset, constraint, and deliverable decomposition;
- dependencies and execution order;
- existing asset reuse analysis;
- risks, unknowns, and approval gates;
- structured plan output consumable by downstream agents.

**Acceptance**: for the LeekParty shop page, GUIF reliably produces a structured plan covering page composition, reused assets, new assets, sizes, formats, QA, and export target.

#### Phase 3: Context and Memory Retrieval

Goal: select relevant project knowledge instead of dumping every file into an agent.

- unified built-in and project workflow loading;
- memory indexing, relevance, priority, and deduplication;
- historical Task and approved-artifact retrieval;
- theme/resource references;
- context budget and trimming report;
- confidence levels for facts, decisions, and lessons.

**Acceptance**: when editing the merchant character, GUIF retrieves relevant rules such as left-side placement, warm golden dusk, noise reduction, and avoidance of pirate motifs without loading unrelated records.

#### Phase 4: Prompt IR and Provider Adapters

Goal: create model-neutral generation instructions instead of binding GUIF to one prompt format.

- Prompt Intermediate Representation;
- composition of theme, resource, layout, history, and negative constraints;
- Provider Adapters that translate Prompt IR into concrete calls;
- prompt versioning and source/result linkage;
- one capability interface for text models, image models, and editing tools.

**Acceptance**: the same Task can run through different providers without changing Runtime, Task, or project data structures.

#### Phase 5: Real Asset Production and Revision Loop

Goal: generate or edit actual assets and register them in the project.

- Generation / Editing Agent;
- separation of effect images and production assets;
- automatic manifest creation and updates;
- protected editing integration;
- revision ancestry and approval status;
- automatic or human-guided correction loop.

**Acceptance**: when the user says “move the character slightly left,” GUIF finds the last approved image and resource, edits only the target area, preserves other pixels, and records a new revision.

#### Phase 6: Layered QA

Goal: expand technical QA into complete UI production QA.

- technical QA for file, size, alpha, and naming;
- visual consistency QA for theme, character, lighting, and noise;
- layout, overlap, readability, and safe-area QA;
- cross-page and cross-asset consistency;
- configurable thresholds and human approval gates;
- actionable revision instructions on failure.

**Acceptance**: a QA failure identifies the violated project rule, affected artifact, and recommended correction.

#### Phase 7: Export, Git, and Delivery Closure

Goal: deliver approved assets safely to game projects with a complete change record.

- incremental export, checksums, and unchanged-asset skipping;
- atlases, nine-slice, fonts, and animation asset types;
- more native engine import integration;
- change sets, Git diff, commit messages, and approval gates;
- rollbackable delivery;
- completion reports and automatic memory capture.

**Acceptance**: the user receives a clear summary of artifacts, QA, exports, and Git changes, with a safe rollback path.

#### Phase 8: Formal ChatGPT / Agent Host Integration

Goal: make natural language a stable primary interface.

- machine-readable Runtime API/CLI protocol;
- host integration guide and error-handling contract;
- confirmation, permission, and high-risk change boundaries;
- multi-turn conversation linkage to the same Task;
- conventions for project selection, progress reporting, and result presentation.

**Acceptance**: a user completes a real UI task without knowing GUIF commands; CLI remains a backend and debugging interface.

### 4. Development Decision Gate

Before implementing any feature, answer:

1. Does it directly serve the natural-language-driven game UI production loop?
2. Which target-architecture responsibility owns it?
3. Does it replace a real gap, or only add another empty interface?
4. Is there an acceptance scenario from LeekParty or another real project?
5. Can the result be verified through a Task, artifact, or report?
6. Does it preserve model independence, project isolation, and Git auditability?
7. Are the current-state and future-phase sections of this file updated?

When these cannot be answered clearly, the default decision is not to build the feature.

### 5. Key Risks

- **Framework overbuild**: interfaces multiply while no real agent completes work.
- **ChatGPT/GUIF disconnect**: CLI runs, but the host cannot reliably invoke or explain it.
- **Context overload**: loading everything increases cost, conflicts, and instability.
- **Unstructured Task state**: a generic dictionary becomes impossible to recover, migrate, or validate.
- **Duplicate Workflow/Pipeline abstractions**: routing and execution diverge.
- **Provider leakage into core**: model independence is lost.
- **Documentation ahead of implementation**: README or specification claims exceed repository facts.

### 6. Open Questions

- Can one shared Task model cover page design, single-asset production, local editing, and batch export?
- Should agent granularity be fixed or project-defined?
- Should Pipeline and Workflow become one concept?
- Is Prompt Builder a core agent or a plugin?
- Should ChatGPT be the default host without becoming a technical dependency?
- Should Memory remain file-retrieval based or use a database/vector index?
- How much visual QA can be automated, and where is human approval mandatory?
- Does GUIF manage only UI artifacts, or also Figma/engine layout implementation?

These assumptions must be validated through real project work, not architecture discussion alone.

### 7. Recommended Next Iteration

Before adding image, Figma, or GitHub agents, prioritize:

1. Task persistence and Run Manifest;
2. unified Pipeline/Workflow design;
3. the first real Planner Agent;
4. the LeekParty medieval-harbor shop page as an end-to-end acceptance case.

Completing these four items moves GUIF from an executable framework contract toward a framework that can complete its first real production task.
