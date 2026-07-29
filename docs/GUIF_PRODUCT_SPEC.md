# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.21`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件是 GUIF 的产品定义、已验证能力、边界、风险和后续迭代基线。产品定位、Runtime、Task、Host、Tool、Approval、Artifact、Visual Review、Revision、Export 或兼容性发生变化时，必须在同一个 Release 或 Pull Request 中更新本文件。

一次 Release 只有在 Feature、Test、CI、中英文 README、Version Metadata 和本文件一致时才算完成。

### 1. 产品定义

GUIF 是一个以自然语言为主要入口、由可配置 Host 调度、通过可配置 Tool 完成具体工作、以 Project File 与 Git 作为长期事实来源、面向游戏 UI 生产全过程的可执行 AI 工作框架。

默认产品路径：

```text
用户
  -> ChatGPT Host                         默认，可替换
  -> GUIF Runtime
       -> Project Context / Retrieval
       -> Workflow / Pipeline
       -> Planner / Director / Theme / Resource / Prompt
       -> Contract QA
       -> Initial Approval
       -> Tool Resolver
            -> Discovery
            -> Connection Workflow
            -> Tool Execution / External Handoff
       -> Artifact Registry
       -> Visual Review
       -> Controlled Revision
       -> Gated Export
```

ChatGPT 在默认路径中承担两个独立角色：

- **ChatGPT Host**：负责对话、确认、调度、Tool Invocation 与结果展示；
- **`chatgpt-image` Tool**：通过 External Callback 完成图片生成和修图。

二者都是默认值，不是 GUIF Core 的硬编码依赖。

### 2. 核心原则

- Host 与 Tool 均可配置；
- ChatGPT-first 默认体验；
- Review Before Execute / Write；
- 生产任务 Fail Closed；
- 不允许隐式 Dry-run Fallback；
- Discovery 不等于安装；
- Connection 必须显式审批；
- 权限、数据范围、外部调用、费用和 Credential 必须披露；
- GUIF 只保存 Credential Reference，不保存 Secret；
- Simulation、Metadata Check 和 Semantic Review 必须区分；
- Revision Source 不覆盖，Replacement 必须通过 Review 后才能 Supersede；
- 所有关键状态必须可持久化、可审计、可恢复。

### 3. alpha.21 已验证能力

#### 3.1 Host Capability Discovery

Runtime 提供 `guif-host-capability-discovery-v1`：

```python
runtime.discover_host()
```

报告包括 Host ID、Capability、Available Tool、Metadata 和 Discovery Timestamp。

默认 ChatGPT Host 声明：

```text
image-generation
image-editing
protected-region-editing
transparent-output
visual-inspection
github-operation
```

#### 3.2 Tool 状态模型

GUIF 现在区分：

```text
registered   当前 Runtime 中存在 Adapter
available    当前 Host 或本地 Runtime 可以使用
installable  Catalog 中存在安装信息，但 Adapter 尚未注册
```

Discovery Record 还包含：

```text
ready
manifest
health
connection_status
host_id
mode
disclosure
```

`available` 不代表用户已经批准绑定到 Project；`installable` 不代表 Tool 已安装或可信。

#### 3.3 Workspace Tool Catalog

可选 Catalog 文件：

```text
.guif/tool-catalog.json
```

Catalog Entry 必须声明：

- Tool ID、Name、Version；
- Capability；
- Install Method 与 Source；
- Permission；
- Data Scope；
- External Call；
- Billable / Unknown Cost；
- Credential Requirement 与 Credential Kind；
- Supported Host。

GUIF 不会根据 Catalog 自动安装 Tool。

#### 3.4 Tool Disclosure

Registered Tool Manifest 与 Catalog Entry 都会输出统一 Disclosure：

```json
{
  "permissions": [],
  "data_scopes": [],
  "external_call": true,
  "cost": "unknown",
  "billable": null,
  "requires_credentials": false,
  "credential_kind": null,
  "supported_hosts": ["chatgpt"]
}
```

Cost 状态为：

```text
billable
no-charge
unknown
```

`unknown` 必须被明确展示，不能默认为免费。

#### 3.5 Connection Request

当 Tool 缺失、未注册或不可用时，Runtime 保持 `waiting-for-tool`。对于非 Reference 文件问题，Runtime 会关联一个 Project 级 Connection Request。

Connection Lifecycle：

```text
pending
  -> approved / rejected
  -> connected
  -> installation-required
  -> waiting-for-credentials
  -> waiting-for-host-support
  -> health-check-failed
  -> unsupported
```

Request 保存：

- Capability 与 Required Capability；
- Tool ID；
- Requested By 与 Reason；
- Tool State；
- Disclosure Snapshot；
- Approval Actor、Comment 与 Timestamp；
- Credential Reference；
- Health Result；
- Recovery Actions；
- Decision History。

#### 3.6 Connection 决策规则

```text
Reject
  -> 不修改 Project Tool Configuration

Approve Registered + Healthy Tool
  -> Bind Project Capability
  -> connected

Approve Installable-only Tool
  -> installation-required
  -> 不自动安装

Approve Credential Tool without reference
  -> waiting-for-credentials

Approve Tool without Host support
  -> waiting-for-host-support / health-check-failed
```

重复执行 Approve 可以在提供 Credential Reference 后继续完成 Connection。

#### 3.7 Credential Policy

允许保存：

```text
env://TOKEN_NAME
secret-manager://project/tool
host-vault://connection-id
```

禁止保存：

```text
API Key Secret
Password
Access Token Value
Private Key Content
```

Connection Record 明确包含：

```json
{
  "secret_stored_by_guif": false
}
```

Credential 的真实解析由 Host、Plugin、运行环境或 Secret Manager 完成。

#### 3.8 Health Check Retry

```python
runtime.retry_tool_health(project, tool_id)
```

每次 Retry 保存 Attempt、Host、Mode、Health Result 与 Timestamp。已经 Approved 的 Request 在配置恢复健康后可以自动进入 `connected`。

#### 3.9 Tool Adapter Contract Test Runner

```python
runtime.run_tool_contract_tests(tool_id)
```

Runner 为 Side-effect-free，不调用外部服务。检查：

- Manifest Schema；
- Adapter / Manifest Identity；
- Capability；
- Input / Output Contract；
- Execution Mode 对应实现；
- Permission / Data Scope / Cost / Credential Disclosure；
- Health Check Identity 和 Status Shape。

Contract Test Passed 不代表：

- Plugin 已安装；
- Plugin 已签名；
- Plugin 来源可信；
- 用户已批准 Connection；
- Tool 可以访问 Production Data。

#### 3.10 持久化

Project 级文件：

```text
projects/<project>/tool-connections.json
```

保存 Connection Requests、Decision History、Disclosure Snapshot、Credential Reference 和 Health Check History。

Task 级文件继续保存于 Run Directory：

```text
tool-resolution.json
tool-handoffs.json
executions.json
artifacts.json
visual-reviews.json
revision-plans.json
revision-execution.json
```

### 4. 已有闭环

当前 GUIF 可以完成：

```text
Project Init
-> Requirement
-> Plan / Direction / Theme / Resource / Prompt
-> Contract QA
-> Initial Approval
-> Tool Discovery / Resolution
-> Connection Request when needed
-> ChatGPT Handoff or Direct Tool
-> External Result Submission
-> Artifact Registration
-> Visual Eligibility / Metadata Review
-> Revision Plan
-> Independent Revision Approval
-> Editing Tool
-> Replacement Artifact
-> Re-review
-> Passing Review gated Supersession
```

### 5. 当前限制

- 不自动安装 Plugin；
- 不动态加载新安装 Adapter；
- Catalog 尚无签名、远程可信校验和 Distribution Metadata；
- Host、Approval Actor 和 Result Submitter 尚未认证；
- GUIF Core 不解析 Credential Reference；
- ChatGPT 产品侧 Handoff 自动 Callback Wiring 尚未完成；
- 默认 Semantic Visual Inspector 仍为空；
- Mask、多 Source Revision 和 Protected Region Package 尚未标准化；
- Export Agent 仍为 Contract-only；
- Git Change Management 未开发。

### 6. 后续迭代

#### alpha.22：Gated Export Agent

- Export Agent 消费 Active Artifact；
- 验证 Contract QA、Visual Review、Revision Resolution；
- 匹配 Resource Contract；
- Materialize Approved Production Asset 到 Project Truth；
- Engine-specific Export Manifest；
- Rollback 与 Audit。

#### alpha.23：Authenticated Host API 与 Git Change Management

- Stable Host Result Protocol；
- Authenticated Host / Actor Identity；
- Result Submission Authorization；
- Git Change Set、Branch、Commit、Rollback；
- Pause、Cancel、Streaming、Summary。

#### alpha.24：Plugin Distribution 与 Trust

- Signed Catalog；
- Dynamic Adapter Loading；
- Dependency Isolation；
- Permission Enforcement；
- Credential Resolver Contract；
- Remote Catalog 与 Version Upgrade。

### 7. 主要风险

- 如何把 ChatGPT Product Tool Call 自动连接到 GUIF Handoff / Result Submission；
- Catalog 和 Plugin 的信任、签名与供应链安全；
- Cost、Latency、Privacy 和 Quality-aware Routing；
- Credential Reference 的跨 Host 可移植性；
- Waiting State 的并发、Lease、Timeout 和 Optimistic Lock；
- Upstream Contract 变化后 Approval、Handoff、Artifact、Revision 和 Connection 是否失效；
- 如何避免 Framework 继续增加 Contract，却没有真实产品侧自动化。

### 8. 迭代记录

- `alpha.9`：Runtime、Task、Agent、Registry、Pipeline Contract。
- `alpha.10`：Persistent Run、Checkpoint、Failure Resume。
- `alpha.11`：Workflow-driven Pipeline 与 Structured Planner。
- `alpha.12`：Structured Director 与 Context Retrieval。
- `alpha.13`：Theme / Resource Agent 与 Review-before-write。
- `alpha.14`：Model-neutral Prompt IR。
- `alpha.15`：Semantic Contract QA。
- `alpha.16`：Persistent Approval 与 Controlled State Transition。
- `alpha.17`：Provider Adapter、Dry-run 与 Artifact Registry。
- `alpha.18`：Visual Artifact Inspection、Revision Plan、Supersession。
- `alpha.19`：Configurable Host / Tool、ChatGPT Bridge、Waiting State、External Submission。
- `alpha.20`：Controlled Revision Job、Independent Revision Approval、Immutable Source、Review-gated Supersession。
- `alpha.21`：Host / Tool Discovery、Registered / Available / Installable State、Connection Request、Disclosure、Credential Reference、Health Retry 与 Contract Test Runner。

---

## English Version

### 0. Purpose

This living document defines GUIF's product scope, verified capabilities, boundaries, risks, and next iteration baseline. It must change in the same release whenever Runtime, Host, Tool, Approval, Artifact, Review, Revision, Export, or compatibility changes.

### 1. Product definition

GUIF is an executable game UI production framework with a natural-language entry point, configurable Hosts, configurable Tools, Project files and Git as durable truth, inspectable execution, and recoverable state.

ChatGPT is the default Host and `chatgpt-image` is the default image generation and editing Tool. They are replaceable defaults, not Core dependencies.

### 2. Verified state at alpha.21

GUIF now exposes a Host capability discovery protocol and distinguishes registered, available, and installable Tools.

A Tool discovery record includes current state, readiness, Manifest or Catalog metadata, Health Check, Project connection status, and permission, data-scope, external-call, cost, credential, and Host-support disclosures.

Workspace installable entries may be declared in `.guif/tool-catalog.json`. Catalog entries are evidence only; GUIF does not auto-install or auto-register them.

When an eligible Tool resolution fails, GUIF keeps the Task in `waiting-for-tool` and links a persisted Project connection request. The user can approve or reject after reviewing disclosures. Approval may produce `connected`, `installation-required`, `waiting-for-credentials`, `waiting-for-host-support`, or `health-check-failed`.

Credentials are represented only by opaque references. GUIF explicitly records that it did not store the secret value.

Health retries are persisted and can complete an already approved connection after configuration becomes healthy.

The Tool Adapter contract-test runner performs no external calls. It validates Manifest identity, capabilities, I/O contracts, execution method, disclosures, and Health Check shape.

### 3. Existing production loop

The alpha.20 controlled Revision lifecycle remains active: Visual findings become separately approved edit Jobs, source files are immutable and hash-verified, replacements receive automatic metadata review, and sources are superseded only after a passing semantic visual review.

### 4. Remaining gaps

- automatic Plugin installation and dynamic Adapter loading;
- signed and remotely verified Catalogs;
- authenticated Host, Approval, and Result identities;
- Credential Reference resolution;
- automatic ChatGPT product-side callback wiring;
- default semantic visual inspection;
- mask and multi-source Revision contracts;
- gated production Export Agent;
- Git change management.

### 5. Next phases

1. `alpha.22`: Gated Export Agent, approved Artifact materialization, engine-specific manifests, rollback, and audit.
2. `alpha.23`: Authenticated Host API, result authorization, and Git change management.
3. `alpha.24`: Plugin distribution, signed Catalogs, dynamic loading, dependency isolation, permission enforcement, and Credential Resolver contracts.

### 6. Main risks

The principal unresolved questions concern ChatGPT product-side automatic callbacks, Plugin supply-chain trust, cost/privacy-aware routing, credential portability, waiting-state concurrency, stale contract invalidation, and avoiding contract growth without real product automation.
