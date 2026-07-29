# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.18`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的与维护规则

本文件是 GUIF 的产品定义、当前能力审阅、风险清单和后续迭代基线，不是一次性 Roadmap 或宣传文案。

发生以下变化时，必须在同一个 Release 或 Pull Request 中同步更新本文件：

- 产品定位、边界或核心原则变化；
- Runtime、Task、Agent、Workflow、Context、Prompt、Approval、Provider、Artifact、Visual Review、Revision、QA 或 Export 等核心能力变化；
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

Agent Host
  -> 选择 Project
  -> GUIF Runtime 加载 Context 并解析 Workflow
  -> Planner / Director / Theme / Resource
  -> Prompt IR 与 Contract QA
  -> Human Approval
  -> Provider Execution
  -> Artifact Registration
  -> Visual Eligibility 与 Metadata Review
  -> Visual Inspection Adapter
  -> Revision Plan / Revision Execution
  -> Gated Export
  -> 保存 Task、Approval、Execution、Artifact、Review、Revision 与 Git Change
```

普通用户主要表达目标和审批关键决定；CLI 用于实现、调试、自动化和 CI。

#### 1.3 核心价值

- **自然语言优先**：用户表达目标，Framework 负责拆解、约束、执行和解释。
- **可执行而非 Prompt Collection**：GUIF 必须产生 Task、Plan、Contract、Approval、Execution、Artifact、Review 和 Revision。
- **Model / Provider Agnostic**：Runtime、Prompt IR、Provider 和 Visual Inspection Contract 不绑定单一服务。
- **Project Isolation**：不同游戏的 Theme、Resource、Memory、Run 和 Artifact 互不污染。
- **Deterministic Contract**：Naming、Dimension、Alpha、Hash、State Transition、Validation 和 Export 尽可能可重复。
- **可审计、可恢复**：每次 Run 必须说明输入、Context、Decision、Execution、Artifact、Failure 和下一步。
- **Review Before Write / Execute**：未经批准不得把推导结果写入 Project Truth 或调用 Provider。
- **Capability Before Invocation**：Provider 与 Visual Inspector 必须声明并满足 Capability。
- **No False Verification**：Simulation、Metadata Check 和 Visual Semantic Review 必须明确区分。
- **Immutable Provenance**：Revision 不覆盖原 Artifact，旧结果保留并通过 Supersession 关联。

#### 1.4 目标架构

```text
User / Agent Host
  -> GUIF Runtime
       -> Context Loader / Retrieval
       -> Workflow Resolver / Pipeline
       -> Agent Registry
            -> Planner
            -> Director
            -> Theme
            -> Resource
            -> Prompt
            -> Semantic Contract QA
       -> Approval Gate
       -> Provider Registry
       -> Artifact Registry
       -> Visual Review Service
            -> Eligibility / Integrity
            -> Image Metadata Inspection
            -> Visual Inspection Registry
            -> Revision Planner
       -> Revision Execution
       -> Visual Recheck
       -> Export Agent
       -> Task Store / Git Change Management
```

职责边界：

- **Agent Host**：理解对话、提供 Identity、处理 Approval、选择 Provider / Inspector 并解释结果。
- **Runtime**：执行生产 Workflow 和受控 Provider 状态转换，不承担具体模型逻辑。
- **Provider Adapter**：接收 `ExecutionRequest`，返回 `ExecutionResult`。
- **Artifact Registry**：保存文件身份、Hash、Provider Metadata、Output Contract、Approval Snapshot 和 Provenance。
- **Visual Review Service**：区分 Simulation 与 Visual Artifact，执行 Integrity / Metadata Check，调用可选 Inspector，并建立 Revision Plan。
- **Visual Inspection Adapter**：只在 Capability 满足时判断 Theme、Composition、Content、Readability、Usability 和 Resource Compliance。
- **Revision Plan**：将 Finding 关联到 Source Job 和 Source Artifact，不直接覆盖原文件。
- **Export Gate**：只有 Contract QA 与所有 Active Visual Artifact Review 均通过时才允许真实 Export。

#### 1.5 非目标

GUIF 不计划：

- 替代 Photoshop、Figma、Unity、Godot 或 Unreal；
- 管理完整游戏逻辑、Server、数值或关卡代码；
- 训练基础模型；
- 成为任意行业的通用 Agent Framework；
- 把 Dry-run Receipt 描述为图片；
- 把 Dimension / Format / Alpha Check 描述为视觉美术质量通过；
- 在没有明确 Approval 的情况下调用 Provider 或修改 Project Truth；
- 为了简化流程而覆盖或删除旧 Artifact 与 Review Provenance。

### 2. GUIF 当前内容与进度

以下结论基于 `v1.0.0-alpha.18` 仓库代码。

状态定义：

- **可用**：能完成明确、可验证的工作；
- **基础可用**：主体存在，但覆盖范围或自动化程度有限；
- **Contract 完成**：Interface 和执行骨架存在，尚未完成真实业务；
- **未开发**：仓库中尚无可用实现。

| 能力 | 当前状态 | 当前实际内容 | 主要缺口 |
|---|---|---|---|
| Project / Git-friendly Store | 可用 | Project 初始化、Run Directory、JSON / JSONL / Markdown 持久化 | Migration、Archive、Retention、Locking |
| Workflow / Pipeline | 基础可用 | Built-in 与 Project Override、Agent Order、Checkpoint、Resume | Branch、Loop、Concurrency、Cancel、Policy Retry |
| Context / Retrieval | 基础可用 | Project Config、Theme、Workflow、Resource、Memory；英文 Token、中文 n-gram、Budget 与 Provenance | Embedding、Historical Run / Artifact Retrieval、Dedup |
| Planner | 基础可用 | Page、Canvas、Orientation、Engine、Reuse、Missing Resource、Risk、Open Question | Typed Component Tree、复杂 Interaction、LLM Adapter |
| Director | 基础可用 | Composition Zone、Focal Order、Constraint、Reuse Decision、Conflict、Approval Point | Reference Image Review、Cross-page Comparison |
| Theme Agent | 基础可用 | Active Theme、Preset 推导、Memory Constraint、Conflict | Version、Inheritance、Visual Token、Materialization |
| Resource Agent | 基础可用 | Existing Reuse、Manifest Candidate、Dimension Source、Engine Hint | Variant、Atlas、Nine-slice、Dependency、Materialization |
| Prompt Agent | 基础可用 | Provider-independent Prompt IR、Job、Constraint、Reference、Output Contract、Capability | Revision Job、Provider-specific Payload Adapter |
| Semantic Contract QA | 基础可用 | Cross-agent Contract、Approval、Execution Gate、Export Gate | 与 Visual Review 的统一 Schema / Policy |
| Approval API | 基础可用 | Approve / Reject / Request Changes、History、Prompt Gate、CLI | Authenticated Identity、Role、Signature、Expiry、Optimistic Lock、Contract Hash Invalidation |
| Provider Adapter | 基础可用 | Request / Result、Capability Gate、Reference Binding、Attempt Persistence | Real Provider、Credential、Quota、Retry、Async |
| Dry-run Provider | 可用 | Deterministic JSON Receipt；无 External Call、无 Billing、无 Pixel | 仅用于 Contract 验证 |
| Artifact Registry | 基础可用 | Artifact ID、Path、SHA-256、MIME、Dimension、Provider / Approval / Prompt Provenance | Remote Storage、Retention、Automatic Supersession Policy |
| Visual Eligibility / Integrity | 可用 | Simulation / Visual 区分；MIME、Path、Existence、SHA-256、Stale Check | Signed Artifact、Remote Reference |
| Image Metadata Review | 可用 | Width、Height、Format、Alpha、Mode、Output Contract 与 Provider Metadata 一致性 | Color Space、ICC、Compression、Multi-resolution |
| Visual Inspection Contract | 基础可用 | Request / Result、Capability、Registry、No-adapter=`not-run` | Built-in / Real Inspector、Confidence、Evidence Artifact |
| Revision Planning | 基础可用 | Finding -> Revision Plan；关联 Source Job / Artifact；Preservation Constraint | Revision Prompt Job、Approval、Execution、Recheck Automation |
| Artifact Supersession | 基础可用 | 显式 Old -> `stale`、`superseded_by`；New -> `supersedes` | 自动策略、Branching Revision、Conflict Handling |
| Protected Editing | 可用 | Mask Composition 与 Protected Pixel QA | 尚未进入 Revision Runtime Loop |
| Visual Semantic QA | Contract 完成 | 可通过外部 Adapter 返回 Passed / Review / Blocked | 默认 Registry 为空；无真实视觉 Model |
| Export | 基础可用 | Generic / Unity / Godot / Unreal Metadata Adapter | Built-in Export Agent 仍是 Contract-only；尚未消费最终 Visual Gate |
| Host / Git Integration | 未开发 | README API / CLI 示例 | Stable Result Protocol、Identity、Streaming、Commit / Rollback |

#### 2.1 当前可以真实完成的闭环

```text
Project Init
-> Context Selection
-> Workflow / Pipeline
-> Plan / Direction / Theme / Resource
-> Prompt IR
-> Contract QA
-> Persistent Approval
-> Provider Capability / Reference Gate
-> Dry-run 或自定义 Provider Execution
-> Artifact Registration
-> Visual Eligibility / File Integrity
-> Image Metadata Review
-> 可选 Visual Inspection Adapter
-> Revision Plan
-> Artifact Supersession
-> 全部状态持久化
```

alpha.18 已经能够做到：

- Dry-run Artifact 自动标记为 `not-applicable`，不会声称视觉通过；
- 真实 Image Artifact 的 File、Hash、MIME、Dimension、Format 和 Alpha 可确定性检查；
- 没有 Inspector 时保持 `not-run` 和关闭 Export Gate；
- Inspector Capability 不足时拒绝调用；
- Finding 可生成带 Source Artifact / Job 的 Revision Plan；
- Replacement Artifact 可显式 Supersede 原 Artifact，并保留旧记录。

#### 2.2 当前尚不能完成的关键闭环

下面需求仍不能由内置能力完全自动完成：

```text
“生成商店页图片，检查构图和可读性，
发现主按钮层级不足后自动修图，再复检并导出 Unity。”
```

当前缺口：

- 没有 Built-in Real Image Provider；
- 没有 Built-in Semantic Visual Inspector；
- Revision Plan 尚不能自动转换为新的 Edit Prompt Job；
- Revision 需要新的 Approval、Provider Execution 和 Source Artifact Binding；
- 新 Artifact 尚未自动触发 Supersession 与 Recheck；
- Export Agent 尚未消费最终 Review Gate。

### 3. 预期待开发内容

#### Phase 1–7：已完成的基础

- Runtime Contract、Task Store、Checkpoint、Resume；
- Workflow-driven Pipeline；
- Planner、Director、Theme、Resource、Prompt、Semantic Contract QA；
- Context Retrieval；
- Persistent Approval；
- Provider Adapter、Dry-run、Artifact Registry。

#### Phase 8：Visual Artifact Inspection + Revision Planning

alpha.18 已完成第一版：

- Visual Artifact Eligibility；
- Safe Path、Existence、Hash 与 MIME Check；
- Image Dimension、Format、Alpha 与 Provider Metadata Check；
- Model-neutral Visual Inspection Request / Result；
- Inspector Capability Registry；
- Simulation=`not-applicable`；No Inspector=`not-run`；
- Persistent Visual Review；
- Finding -> Revision Plan；
- Explicit Artifact Supersession；
- Visual Review / Revision Run Summary 与 CLI。

仍待：

- Review Schema Migration；
- Confidence、Evidence Image / Region；
- Cross-page Review；
- Automatic Review Invalidation after Artifact or Contract changes。

#### Phase 9：Revision Job Construction + Controlled Revision Execution

下一迭代目标：把已批准 Revision Plan 转换成真正可执行、可审计的 Edit Job。

需要包含：

- Revision Plan -> Versioned Prompt Job；
- Source Artifact 作为 Immutable Bound Reference；
- Finding 与 Objective 转换为 Edit Instruction；
- Protected Region / Mask Contract；
- 新 Revision Approval Point；
- Editing Provider Capability Gate；
- Revision Attempt / Failure Persistence；
- Replacement Artifact 自动链接 Source Artifact；
- 明确 Supersession Policy；
- 自动 Visual Recheck。

**验收标准**：未经 Revision Approval 不得执行；Source Artifact 不得被覆盖；新 Artifact 必须保留 Revision、Finding、Approval 与 Provider Provenance；失败后旧 Artifact 继续有效。

#### Phase 10：Real Provider + Built-in Visual Inspector

- 至少一个真实 Generation / Editing Provider；
- Credential / Secret Boundary；
- Cost、Quota、Rate Limit、Retry 和 Async；
- 至少一个真实 Visual Inspection Adapter；
- Confidence、Evidence 和 Human Review Policy。

#### Phase 11：Production Export、Host 与 Git Integration

- Real Export Agent 消费 Artifact、Approval、Contract QA 与 Visual Review Gate；
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
7. 是否明确区分 Simulation、Metadata Check 与 Semantic Visual Review？
8. 是否保留 Source Artifact 与全部 Provenance？
9. 是否同步更新中英文 README、Version Metadata 和本文件？

### 5. 主要风险与待验证假设

- Rule-based Planner 是否能长期保持可维护；
- Mutable Task 是否需要 Typed Subtask；
- Approval、Review 与 Artifact 是否需要 Contract Hash、Version 和 Expiry；
- 多 Host 同时 Approval / Execute / Review 时如何避免 Lost Update；
- Inspector Result 的 Confidence 与 Evidence 如何标准化；
- Metadata Passed + Semantic Passed 是否足以打开 Export，还是仍需 Human Approval；
- Visual Inspector Capability 应按固定维度还是允许 Project 扩展；
- Revision Plan 如何避免不断累积但无人执行；
- Artifact Supersession 是显式操作还是成功 Recheck 后自动执行；
- Real Provider Credential 应位于 Runtime、Host 还是 Plugin Boundary；
- Artifact Store 何时需要 Database / Object Storage；
- 如何避免 Interface 增长快于真实视觉生产闭环。

### 6. 迭代记录

- `alpha.9`：Runtime、Task、Agent Registry、Pipeline Contract 和 Context Loading。
- `alpha.10`：Task schema v2、Persistent Run Store、Checkpoint、Failure、Load / List / Resume。
- `alpha.11`：Workflow-driven Pipeline 和 Structured Planner。
- `alpha.12`：Relevance Context Selection 和 Structured Director。
- `alpha.13`：Structured Theme / Resource 与 Review-before-write。
- `alpha.14`：Model-neutral Prompt IR。
- `alpha.15`：Semantic Contract QA、Finding、Revision Request、Artifact Review State 和 Export Gate。
- `alpha.16`：Persistent Approval API、受控 Prompt Job Gate、QA 自动刷新和 Approval CLI。
- `alpha.17`：Provider Adapter、Capability / Reference Gate、Dry-run、Execution Persistence 和 Artifact Registry。
- `alpha.18`：Visual Eligibility / Integrity、Image Metadata Review、Visual Inspection Contract、Persistent Review、Revision Plan 与 Artifact Supersession。

---

## English Version

### 0. Purpose and maintenance

This file is GUIF's living product definition, verified capability review, risk register, and iteration baseline. It must change in the same release or pull request whenever product scope, architecture, capability status, compatibility, priorities, risks, or assumptions change.

A release is complete only when Feature, Tests, CI, both READMEs, Version Metadata, and this specification agree.

### 1. Expected product

GUIF is an executable AI work framework for end-to-end game UI production. Natural language is the primary interface, an Agent Host manages conversation and identity, and Git plus Project files remain the long-term source of truth.

Expected flow:

```text
Requirement
-> Context and Workflow
-> Plan / Direction / Theme / Resource
-> Prompt IR and Contract QA
-> Approval
-> Provider execution
-> Artifact registration
-> Visual eligibility and metadata inspection
-> Visual Inspection Adapter
-> Revision Plan and controlled revision
-> Visual recheck
-> gated Engine-ready Export
```

Core principles are provider independence, Project isolation, deterministic contracts, inspectable Runs, explicit Approval, capability gates, no false visual verification, and immutable Artifact provenance.

### 2. Verified state at alpha.18

GUIF can execute deterministic Planner, Director, Theme, Resource, Prompt, and Contract QA Agents; persist Approvals; execute approved Prompt jobs through Provider Adapters; and register Artifacts with file identity and provenance.

Alpha.18 adds a Visual Review Service that:

- rejects stale, missing, corrupted, unsafe-path, or unsupported image Artifacts;
- classifies simulations and non-visual receipts as `not-applicable`;
- checks real images for file hash, MIME, dimensions, format, Alpha, and Provider metadata consistency;
- creates model-neutral Visual Inspection Requests;
- enforces Inspector capabilities;
- preserves `not-run` when no Inspector exists;
- persists Visual Review records and Revision Plans;
- supports explicit Artifact supersession while retaining old provenance.

A capable external Inspector may return `passed`, `review-required`, or `blocked`. Only passing Contract QA plus passing review for every active visual Artifact opens the aggregate Export Gate. The default Inspector Registry is empty, so GUIF does not claim semantic visual approval by itself.

The remaining gap is specific: GUIF can identify and plan a revision, but it cannot yet convert that plan into a new approved edit Job, execute the revision, automatically link the replacement Artifact, recheck it, and perform real gated Export.

### 3. Expected development

1. Build versioned Revision Jobs from Revision Plans.
2. Bind the source Artifact as an immutable edit reference.
3. Add Revision Approval, editing capability gates, attempt persistence, replacement linking, supersession policy, and automatic recheck.
4. Integrate at least one real Generation / Editing Provider and one real Visual Inspector.
5. Implement a real Export Agent consuming Approval, Artifact, Contract QA, and Visual Review gates.
6. Add stable Host identity, streaming, pause, Git change management, and end-to-end acceptance tests.

The immediate alpha.19 acceptance target is that a proposed revision cannot execute without approval, cannot overwrite the source Artifact, and must create a replacement Artifact whose provenance links the Finding, Revision Plan, Approval, Provider attempt, and source Artifact.

### 4. Main risks

Important unresolved questions include Contract hash invalidation, authenticated identity, concurrent writers, Inspector confidence and evidence, Human versus automated final approval, extensible review dimensions, revision backlog control, explicit versus automatic supersession, Provider credential boundaries, and file-store scalability.

### 5. Iteration history

- `alpha.9`: Runtime contracts and Context loading.
- `alpha.10`: persistent Task Runs and recovery.
- `alpha.11`: Workflow-driven Pipelines and Structured Planner.
- `alpha.12`: relevance retrieval and Structured Director.
- `alpha.13`: Structured Theme / Resource and review-before-write.
- `alpha.14`: model-neutral Prompt IR.
- `alpha.15`: Semantic Contract QA and Export Gate.
- `alpha.16`: persistent Approval and controlled execution state.
- `alpha.17`: Provider Adapter, Dry-run execution, and Artifact Registry.
- `alpha.18`: Visual Artifact eligibility, deterministic image metadata inspection, Visual Inspection Contract, persisted review, Revision Planning, and Artifact supersession.
