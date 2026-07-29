# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.27`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF 的产品定位、alpha.27 已验证能力、隐私和安全边界、失败策略、兼容性、验收标准与下一阶段。Feature、Test、CI、中英文 README、Version Metadata 与本规格必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、自然语言优先、Host 与 Tool 均可配置、面向游戏 UI 全生产流程的可执行 AI 工作框架。

GUIF Core 负责：

```text
Project / Private Theme / Conversation Context
Planning / Direction / Contract / Prompt
Approval / Tool Routing / Work Coordination
Artifact / Provenance / Review / Revision
Export / Rollback / Git Change / Audit
Conversation State / Recovery
```

真实图片生成、图片修改和语义视觉理解由经过配置的 Host 与 Tool 执行。默认组合：

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

以上均为默认契约，不是不可替换的 Core 依赖。

### 2. alpha.27 默认用户路径

```text
开始或恢复 Conversation
  -> 确认、选择、创建、派生或明确跳过 Private Theme
  -> 用自然语言描述页面或资源需求
  -> Planner / Director / Resource / Prompt IR
  -> Contract QA
  -> Conversation Stage: approval-required
  -> 用户批准
  -> 自动处理 Approval ID、Task Etag 和 Exclusive Lease
  -> Tool Resolver
  -> Private Host Work: image-generation 或 image-editing
  -> ChatGPT Host 调用真实图片 Tool
  -> Artifact Registry
  -> Eligibility + File Identity + Metadata Review
  -> Private Host Work: visual-inspection
  -> chatgpt-vision Semantic Result
       -> passed
       -> review-required
       -> blocked
  -> Actionable Finding 形成 Revision Plan 与 Revision Job
  -> Conversation Stage: revision-approval-required
  -> 独立 Revision Approval
  -> Controlled Editing Loop
  -> Conversation Stage: ready-to-export
  -> Authenticated Gated Export
```

正常用户路径只需要：

```text
project
conversation_id
自然语言需求
approve / request-changes / reject / continue / export
```

默认不要求用户操作：

```text
Task ID
Approval ID
Revision ID
Task Etag
Task Lease Token
Work ID
Work Claim Token
Handoff ID
Callback ID
Artifact ID
Private Path
```

### 3. 核心产品原则

1. Theme 是用户拥有的私有、可版本化长期数据，不属于框架 Git；
2. 对话开始时先确认 Theme，不从公开框架示例推断用户真实主题；
3. ChatGPT 默认执行图片生成、修图和视觉理解，但 Host 与 Tool 可配置；
4. GUIF 不伪造 Pixel，也不把 `dry-run` Receipt 当成图片；
5. Metadata Review 不能声明 Theme、构图、可读性或可用性已经通过；
6. Semantic Visual Conclusion 必须来自明确的 Visual Inspector Result；
7. Initial Approval 不自动授权后续 Revision；
8. Replacement Artifact 只有在视觉检查通过后才能 Supersede Source；
9. 生产写操作必须关联 Authenticated Actor、Capability、Task Etag 和必要 Lease；
10. Conversation Service 可以隐藏底层标识，但不能绕过底层安全契约；
11. Request Replay 必须幂等，Key 冲突必须 Fail Closed；
12. 私有 Theme、Prompt、Conversation Record、Work、Claim、Finding 和 Runtime Evidence 默认不进入公共仓库。

### 4. Private Conversation Workflow Contract

Conversation Record 保存在：

```text
<private-data-root>/conversation-workflows/<project>/conversation-<sha256>.json
```

Record 至少包含：

```text
schema_version
conversation_id
project
status
continue_unbound
active_task_id
request_records
checkpoint
history
created_at
updated_at
```

`active_task_id` 只存在于 Private Record。默认 User View 不返回该值。

Conversation Record 不允许保存：

```text
Bearer Token
Task Lease Token
Work Claim Token
Credential Verifier
Raw Image Bytes
Full private Theme content
```

### 5. User-facing Conversation View

默认 View Schema：

```text
schema_version
conversation_id
project
status
stage
message
theme
actions
artifacts
recovery
updated_at
```

Artifact Summary 只返回用户需要的信息：

```text
kind
operation
status
review_status
mime_type
width
height
```

开发和支持场景可以显式请求 Diagnostics。Diagnostics 不是默认产品路径。

### 6. Conversation Stages

alpha.27 支持以下主要 Stage：

```text
theme-confirmation
ready-for-request
approval-required
changes-required
ready-to-produce
image-production
visual-review
revision-approval-required
revision-changes-required
revision-ready
tool-configuration-required
ready-to-export
recoverable-error
cancelled
completed
attention-required
```

Stage 必须由 Persisted Task、Approval、Host Work、Artifact、Visual Review、Revision 和 Export Evidence 推导，不能只依赖内存状态。

每个 Stage 返回与当前上下文匹配的 Action，例如：

```text
select-theme
create-theme
continue-unbound
submit-request
approve
request-changes
reject
continue
run-host
retry
recover
export
```

### 7. Theme Resolution

新 Conversation 如果没有 Conversation-level Theme Binding，必须进入 `theme-confirmation`。

支持：

```text
select_theme
create_theme
derive_theme
continue_unbound
```

`continue_unbound` 必须是显式决定，不能成为静默默认值。

Conversation Binding 优先于 Project Binding。Task 持久化只保存 Private Theme Reference：

```text
theme_id
version
snapshot_hash
privacy
```

完整 Theme 只在 Private Runtime Boundary 内 Hydrate。

### 8. Request Idempotency

`submit(...)` 接受 `request_key`。

确定性 Request Hash 覆盖：

```text
project
conversation_id
requirement
pipeline
```

规则：

```text
相同 Key + 相同 Hash -> 返回已有 Task 状态
相同 Key + 不同 Hash -> Fail Closed
新 Key -> 创建新 Task
```

Conversation Service 在 Task 中写入 Private Workflow Reference，便于 Session Record 丢失时恢复。

### 9. Approval Orchestration

`conversation.approve(...)` 根据当前 Stage 决定操作对象：

```text
approval-required
  -> 当前全部 Pending Initial Approval Point
  -> 逐个获取一次性 Task Lease
  -> Authenticated Approval Decision
  -> 自动准备第一个未执行 Prompt Job

revision-approval-required
  -> 当前 Pending Revision Approval
  -> 独立 Authenticated Revision Decision
  -> 自动准备对应 image-editing Job
```

`request_changes(...)` 与 `reject(...)` 使用同样的 Contextual Resolution，但不会继续执行 Tool。

Conversation Service 不允许用 Initial Approval 代替 Revision Approval。

### 10. Host Execution Orchestration

`run_host_until_blocked(...)` 接受 Host 提供的：

```text
image_executor(work, attachments)
visual_inspector(work, attachments)
```

Service 自动协调：

```text
Work Discovery
Task Scoping
Task Etag
Exclusive Task Lease
Actor-bound Work Claim
Immutable Attachment Retrieval
Image or Visual Result Submission
Artifact Registration
Metadata Review
Semantic Review
Stage Refresh
```

Task Scoping 是 alpha.27 的强制要求。一个 Conversation 的 Host Loop 不能消费另一个 Conversation 的 Work。

本地 Python Package 无法自行访问 ChatGPT 产品内部图片 Tool。Callable 或 Gateway Consumer 必须由宿主环境提供。

### 11. Visual Review and Revision

Metadata Review 检查：

```text
Artifact status
visual / simulation flags
supported MIME
Run path confinement
file existence
SHA-256
actual dimensions
actual format
alpha requirement
registered metadata
Output Contract
```

Metadata 通过后状态仍是 `not-run`，直到 Authenticated Semantic Result 到达。

Semantic Status：

```text
passed
review-required
blocked
```

Actionable Finding 创建或复用 Deterministic Revision Plan，并自动构建 Versioned Revision Job。Revision Job 保持 `approval-pending`，Source Artifact 保持 Active。

只有 Replacement Semantic Review 为 `passed` 时：

```text
source.status = stale
source.superseded_by = replacement
replacement.supersedes += source
revision.supersession_status = completed
```

### 12. Recovery Contract

每次 User View Refresh 都持久化 Checkpoint：

```text
stage
task_status
task_etag
artifact_count
recorded_at
```

`recover(...)`：

1. 读取 Private Conversation Record；
2. 尝试加载 Active Task；
3. Active Reference 丢失时，扫描 Private Task Run；
4. 根据 `conversation_theme.conversation_id` 或 `conversation_workflow.conversation_id` 找到最新匹配 Task；
5. 重新计算 Host Work、Approval、Revision、QA 和 Export Stage；
6. 更新 Private Checkpoint。

`retry(...)`：

```text
failed Pipeline Task -> 从 next_agent_index 恢复
waiting-for-tool -> 配置完成后重新执行 Pending Job
其他状态 -> 拒绝不安全 Retry
```

Recovery 不创建替代图片、不伪造 Tool Result、不自动批准用户 Gate。

### 13. CLI Contract

新增：

```text
guif-conversation
```

主要命令：

```text
open
status
theme-list
theme-select
theme-create
theme-derive
theme-unbound
submit
approve
request-changes
reject
continue
export
recover
retry
```

生产 Mutation 使用环境变量：

```text
GUIF_HOST_TOKEN
```

CLI 不接收或打印 Lease Token 与 Work Claim Token。

### 14. Private Data Boundary

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  conversation-workflows/
  project-theme-bindings/
  host-credentials/
  host-work/
  gateway-requests/
  operation-ledger/
  runs/
  plans/
  migrations/
  privacy-reports/
```

框架 Git 只允许：

```text
代码
Schema
通用文档
完全虚构且不可关联到用户项目的测试 Fixture
```

### 15. Compatibility

alpha.27 保留：

- `Runtime.run(...)`、Task ID API 与现有 CLI，供开发、自动化和兼容场景使用；
- `ChatGPTHostLoop.run_once(...)`，新增可选 `task_id` Scope，不破坏旧调用；
- alpha.25 Gateway Work Endpoint；
- alpha.24 Authenticated Host Callback、Task Lease 与 Git Change；
- alpha.23 Private Theme Library 与 Legacy Migration；
- `ProviderAdapter` Compatibility Layer；
- `dry-run` 显式测试路径。

Conversation-first Workflow 是新的默认产品入口，不删除底层 API。

### 16. alpha.27 验收标准

Release 必须证明：

1. 新 Conversation 在 Theme 未确认时不能启动 Production Task；
2. User View 默认不包含 Task ID、Etag、Lease、Claim、Handoff 或 Callback；
3. Private Conversation Record 位于 Project Git 之外；
4. 相同 Request Key 不会创建重复 Task；
5. Request Key 冲突会 Fail Closed；
6. Initial Approval 可以通过单一 Conversation Action 完成并进入 Image Work；
7. Visual Finding 会进入独立 Revision Approval；
8. Revision 未批准时不会执行图片编辑；
9. Host Loop 只消费 Active Conversation Task 的 Work；
10. Session Task Reference 丢失后可以从 Private Task Run 恢复；
11. Real Artifact 仍必须经过 Metadata 与 Semantic Review；
12. 三个受支持 Python 版本的 CI Matrix 全部通过。

### 17. 当前限制

- ChatGPT 产品必须嵌入 Conversation/Host Loop 或消费 Gateway；仓库无法自行接入 ChatGPT 内部 Tool Runtime；
- Semantic Inspector 是 External Authenticated Result Contract，不是本地自主视觉模型；
- Conversation、Work 与 Task 使用 File-backed 本地协调，不是分布式一致性系统；
- Private Storage 尚未提供静态加密、远程同步、Retention Policy 或多设备冲突处理；
- Conversation CLI 不能从独立终端直接调用 ChatGPT 内部图片 Tool；
- Current-tree Privacy Audit 无法证明 Git History、Fork、Cache 或外部 Clone 已清理。

### 18. 下一阶段

**alpha.28：Usability Freeze and Beta Readiness**

优先级：

```text
一键 Onboarding
Private Backup / Restore
Schema Migration
Failure Diagnostics
End-to-end Sample Validation
Compatibility Guarantees
MVP Scope Freeze
beta.1 Release Checklist
```

---

## English Version

### 0. Document purpose

This living specification defines GUIF's product position, verified alpha.27 capabilities, privacy and security boundaries, failure behavior, compatibility, acceptance criteria, and next phase. Feature code, tests, CI, both READMEs, version metadata, and this specification must remain synchronized in one release.

### 1. Product definition

GUIF is a local-first, natural-language-first, executable AI work framework for end-to-end game UI production with configurable Hosts and Tools.

GUIF Core owns:

```text
Project / Private Theme / Conversation Context
Planning / Direction / Contract / Prompt
Approval / Tool Routing / Work Coordination
Artifact / Provenance / Review / Revision
Export / Rollback / Git Change / Audit
Conversation State / Recovery
```

Configured Hosts and Tools perform real image generation, image editing, and semantic visual inspection. Defaults are:

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

These are replaceable contracts, not hard-coded Core dependencies.

### 2. Alpha.27 default user path

```text
open or recover Conversation
  -> confirm, select, create, derive, or explicitly skip Private Theme
  -> describe UI work in natural language
  -> Planner / Director / Resource / Prompt IR
  -> Contract QA
  -> Conversation Stage: approval-required
  -> user approval
  -> hidden Approval ID, Task etag, and exclusive lease handling
  -> Tool Resolver
  -> Private Host Work: image-generation or image-editing
  -> ChatGPT Host invokes a real image Tool
  -> Artifact Registry
  -> eligibility + file identity + metadata review
  -> Private Host Work: visual-inspection
  -> chatgpt-vision semantic result
       -> passed
       -> review-required
       -> blocked
  -> actionable Finding creates Revision Plan and Revision Job
  -> Conversation Stage: revision-approval-required
  -> independent Revision Approval
  -> controlled editing loop
  -> Conversation Stage: ready-to-export
  -> authenticated Gated Export
```

The normal user path requires only Project, Conversation ID, natural-language input, and contextual actions. It does not require direct manipulation of Task IDs, Approval IDs, Revision IDs, etags, leases, work claims, handoffs, callbacks, Artifact IDs, or private paths.

### 3. Product principles

1. Themes are private, user-owned, versioned long-term data outside framework Git.
2. A conversation confirms Theme before production and never infers a real user Theme from public examples.
3. ChatGPT is the default image, editing, and vision environment, while Hosts and Tools remain configurable.
4. GUIF never fabricates pixels or treats `dry-run` receipts as images.
5. Metadata review cannot claim theme, composition, readability, or usability passed.
6. Semantic visual conclusions require an explicit Visual Inspector Result.
7. Initial Approval never authorizes a later Revision.
8. A replacement supersedes its source only after passing visual review.
9. Production mutations remain bound to authenticated actors, capabilities, Task etags, and required leases.
10. The conversation facade may hide low-level identifiers but may not bypass their contracts.
11. Request replay is idempotent and key conflicts fail closed.
12. Private Themes, prompts, conversation records, work, claims, findings, and runtime evidence stay outside public repositories by default.

### 4. Private Conversation Workflow contract

Records are stored at:

```text
<private-data-root>/conversation-workflows/<project>/conversation-<sha256>.json
```

The record contains schema, conversation and project identity, unbound confirmation, active private Task reference, idempotency records, checkpoint, history, and timestamps. It never stores bearer tokens, lease tokens, work claim tokens, credential verifiers, raw image bytes, or full Theme content.

### 5. User-facing view and stages

The default view returns conversation identity, Project, Stage, message, Theme summary, contextual actions, safe Artifact summaries, recovery status, and update time.

Supported stages include:

```text
theme-confirmation
ready-for-request
approval-required
changes-required
ready-to-produce
image-production
visual-review
revision-approval-required
revision-changes-required
revision-ready
tool-configuration-required
ready-to-export
recoverable-error
cancelled
completed
attention-required
```

Stages are derived from persisted Task, Approval, Host Work, Artifact, Review, Revision, and Export evidence rather than transient memory.

### 6. Theme resolution and request idempotency

A new Conversation without a Conversation-level Theme binding enters `theme-confirmation`. Supported choices are historical selection, creation, immutable derivation, or explicit unbound continuation.

`submit(...)` hashes Project, Conversation, requirement, and pipeline. The same key and hash return existing state. The same key with a different hash fails closed.

### 7. Approval and Host orchestration

Contextual `approve(...)` resolves either pending initial Approval points or the current pending Revision. Initial approval can prepare the first unexecuted Prompt Job; Revision approval can prepare only the corresponding image-editing Job.

`run_host_until_blocked(...)` coordinates work discovery, Task scoping, etag, exclusive lease, actor-bound claim, immutable attachments, result submission, Artifact registration, metadata review, semantic review, and Stage refresh. It must not consume work belonging to another Conversation Task.

The local package cannot access ChatGPT-internal image tools on its own. The Host supplies real image and vision callables or consumes the authenticated Gateway.

### 8. Recovery

Every refreshed view persists a checkpoint with Stage, Task status, Task etag, Artifact count, and timestamp.

`recover(...)` reconciles the private Conversation Record with persisted Task Runs and Host Work. A missing active Task reference can be reconstructed from private conversation bindings. `retry(...)` resumes a failed pipeline from its persisted agent index or retries a configured Tool wait; unsafe states are rejected.

Recovery never fabricates results or auto-approves user gates.

### 9. CLI and compatibility

`guif-conversation` provides open, status, Theme selection/creation/derivation, submit, contextual decisions, continue, export, recover, and retry. Production mutations read `GUIF_HOST_TOKEN` and never print lease or claim secrets.

Existing low-level Runtime, CLI, Gateway, Host Work, Provider compatibility, and explicit `dry-run` APIs remain available. The conversation workflow is the new default product entry, not a removal of developer APIs.

### 10. Alpha.27 acceptance criteria

The release must prove Theme confirmation blocks premature production, default views hide low-level identities, conversation records stay outside Git, idempotency prevents duplicates, approval and revision paths remain distinct, Host execution is Task-scoped, lost session references recover from private Task Runs, real Artifacts still require metadata and semantic review, and the supported Python CI matrix passes.

### 11. Current limitations

The ChatGPT product must embed the Conversation/Host loop or consume the Gateway. The semantic inspector is an authenticated external result contract. Coordination is local file-backed rather than distributed. Private storage lacks encryption at rest, remote sync, retention policy, and multi-device conflict resolution. The standalone CLI cannot invoke ChatGPT-internal image tools. Current-tree privacy audits cannot prove historical copies were removed.

### 12. Next phase

**alpha.28: Usability Freeze and Beta Readiness**

Priorities are one-command onboarding, private backup/restore, schema migration, failure diagnostics, end-to-end sample validation, compatibility guarantees, MVP scope freeze, and the `beta.1` release checklist.
