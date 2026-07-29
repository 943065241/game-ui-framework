# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.26`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF 的产品定位、alpha.26 已验证能力、安全与隐私边界、失败策略、兼容性、当前限制和下一阶段。Feature、Test、CI、中英文 README、Version Metadata 与本规格必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、以自然语言为主要入口、Host 与 Tool 均可配置、面向游戏 UI 全生产流程的可执行 AI 工作框架。

GUIF Core 负责：

```text
Project / Theme / Conversation Context
Planning / Direction / Contract / Prompt
Approval / Tool Routing / Work Coordination
Artifact / Provenance / Review / Revision
Export / Rollback / Git Change / Audit
```

真实图片生成、图片修改和语义视觉理解由经过配置的 Host 与 Tool 执行。默认组合为：

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

以上均为默认契约，不是不可替换的 Core 依赖。

### 2. alpha.26 默认生产路径

```text
新对话确认私有 Theme
  -> Planner / Director / Resource / Prompt IR
  -> Contract QA
  -> Initial Approval Gate
  -> Tool Resolver
  -> chatgpt-image Handoff
  -> Private Host Work: image-generation 或 image-editing
  -> Authenticated Claim + Task Etag + Exclusive Lease
  -> ChatGPT Host 真正调用图片 Tool
  -> Authenticated Result Submission
  -> Artifact Registry
  -> Eligibility + File Identity + Metadata Review
  -> Private Host Work: visual-inspection
  -> chatgpt-vision Semantic Result
       -> passed
       -> review-required
       -> blocked
  -> Actionable Finding 自动形成 Revision Plan 与 Revision Job
  -> Independent Revision Approval
  -> Controlled Editing Loop
  -> Gated Export
  -> Git Change Set / Commit / Revert
```

### 3. 核心产品原则

1. Theme 是用户拥有的私有、可版本化长期数据，不属于框架 Git；
2. ChatGPT 默认执行图片生成、修图和视觉理解，但 Host 与 Tool 可配置；
3. GUIF 不伪造 Pixel，也不把 Dry-run Receipt 当成图片；
4. Metadata Review 不能声明 Theme、构图、可读性或可用性已经通过；
5. 语义视觉结论必须来自明确的 Visual Inspector Result；
6. 生产任务缺少 Tool 时进入可恢复等待状态，不静默回退到 `dry-run`；
7. Host 写操作必须关联 Authenticated Actor、Capability、Task Etag 和必要的 Lease；
8. Work Claim、Task Lease、Callback 和 Result 必须绑定同一 Project、Task、Actor 与 Credential；
9. Source Artifact、Reference 和 Attachment 在执行时重新校验路径、存在性与 SHA-256；
10. Initial Approval 不自动授权后续 Revision；
11. Replacement Artifact 只有在视觉审查通过后才能 Supersede Source；
12. 私有 Theme、Prompt、Work、Claim、Review Finding 和 Runtime Evidence 默认不进入公共仓库。

### 4. Private Host Work Contract

alpha.26 新增私有、可领取的 Host Work Queue：

```text
<private-data-root>/host-work/<project>/work-*.json
```

支持的 Work Kind：

```text
image-generation
image-editing
visual-inspection
```

Work Record 至少包含：

```text
schema_version
work_id
project / task_id
kind / capability
status
host_id / tool_id
handoff_id / artifact_id
request
attachments
submission_contract
claim
result
created_at / updated_at
```

状态：

```text
available
claimed
completed
```

Claim 过期后，Work 可重新回到 `available`。已经完成的 Work 不会再次领取或重复执行。

### 5. Image Work Construction

当 `chatgpt-image` 或其他 External-callback Tool Handoff 处于 `waiting-for-result` 时，GUIF 会生成确定性的 Image Work。

Operation 映射：

```text
generate -> image-generation
edit     -> image-editing
```

Image Work 保留完整执行上下文：

- Prompt Job 与 Output Contract；
- Approval Snapshot；
- Required Capabilities；
- Negative Constraints；
- Acceptance Criteria；
- Tool、Host、Execution 与 Handoff Identity；
- 已绑定 Reference；
- Result Submission Contract。

GUIF 不在构建 Work 时调用图片模型。

### 6. Claim Security

领取 Work 需要：

```text
host-work:claim Capability
Active Host Credential
Work status = available
30–1800 秒 TTL
```

领取成功后只返回一次：

```text
guifw1.<work-id>.<secret>
```

持久化记录只保存 Token SHA-256，不保存原始 Secret。

Claim 绑定：

```text
actor_id
credential_id
claimed_at
expires_at
ttl_seconds
```

以下情况 Fail Closed：

- Claim Token 格式错误；
- Work ID 不匹配；
- Token Hash 不匹配；
- Actor 或 Credential 不匹配；
- Claim 已过期；
- Work 已完成或被其他 Actor 领取。

### 7. Immutable Attachments

Image Editing 与 Visual Inspection Work 可以携带 Attachment Descriptor：

```text
attachment_id
label
storage_scope
path
sha256
size_bytes
mime_type
role
```

允许的 Storage Scope：

```text
private-run
project
```

下载 Attachment 时，GUIF 重新检查：

1. Path 仍处于允许 Root 内；
2. 文件仍然存在；
3. 文件是普通 File；
4. 实际 SHA-256 等于 Descriptor；
5. Claim 属于当前 Authenticated Actor。

因此，修图 Host 获取的是明确绑定的 Source Artifact，而不是名称相似或后来替换的文件。

### 8. Image Result Completion

Image Work Result 要求：

```text
host-work:complete
tool-result:submit
Valid Work Claim
Active Task Lease
Matching Task Etag
Non-empty binary content
Filename / MIME
Optional declared SHA-256
Optional width / height / model_id
```

Completion 复用 alpha.24/25 的 Authenticated Callback Contract：

```text
Work Identity
  -> Handoff Identity
  -> Host / Tool Identity
  -> Task Etag / Lease
  -> Content SHA-256
  -> Artifact Registration
  -> Callback Evidence
```

成功后：

- Work 标记为 `completed`；
- 真实文件登记为 `visual: true`、`simulation: false` Artifact；
- Artifact 保留 Host Work、Callback、Execution、Approval 与 Prompt Provenance；
- 自动开始 deterministic visual eligibility 和 metadata review；
- Metadata 通过后创建 `visual-inspection` Work。

### 9. Deterministic Metadata Review

自动检查：

```text
Artifact status
visual / simulation flags
supported image MIME
Run path confinement
file existence
SHA-256 identity
actual dimensions
actual image format
alpha requirement
registered dimensions
Output Contract dimensions / format / alpha
```

结果可能为：

```text
blocked
not-applicable
not-run
```

只有 Metadata 通过且尚无 Semantic Result 时，Artifact 保持 `not-run`。GUIF 不会把 Metadata 通过描述为视觉设计通过。

### 10. Default Semantic Visual Inspector Contract

默认 Inspector ID：

```text
chatgpt-vision
```

Visual Work 的 Request 包含：

```text
Artifact file identity
Output Contract
Global Contract
Instructions
Negative Constraints
Acceptance Criteria
Review Dimensions
```

默认 Review Dimensions：

```text
theme-consistency
composition-and-hierarchy
content-correctness
readability
usability
resource-compliance
```

提交结果必须选择：

```text
passed
review-required
blocked
```

Finding Severity：

```text
blocking
review
warning
info
```

只有 Authenticated Inspector Result 才会设置：

```text
visual_conclusion_claimed = true
```

Inspector ID、Capability、Result Status 和 Finding Schema 均会校验。

### 11. Automatic Revision Construction

当 Semantic Result 包含 `blocking`、`review` 或 `warning` Finding 时，GUIF：

1. 创建或复用 Deterministic Revision Plan；
2. 将 Finding Message 转换为 Revision Objective；
3. 绑定 Source Artifact、Source Job、Review 与 Finding ID；
4. 自动构建 Versioned Revision Job；
5. 将 Revision Job 保持为 `approval-pending`；
6. 不自动执行修图；
7. 不使 Source Artifact 失效。

用户或获授权 Actor 批准 Revision 后，Revision Job 才能进入 `image-editing` Work。

Replacement 提交后继续执行 Metadata 和 Semantic Review。只有 `passed` 才执行 Supersession。

### 12. Embeddable ChatGPT Host Loop

`ChatGPTHostLoop` 是 Host-side SDK，不是 GUIF 内置图片模型。

Host 提供两个 Callable：

```text
image_executor(work, attachments) -> image result
visual_inspector(work, attachments) -> semantic result
```

SDK 负责：

```text
Work Discovery
Task Etag
Task Lease
Work Claim
Attachment Download
Result Submission
Artifact Registration
Visual Work Preparation
Failure-safe Lease Release
```

Callable 负责：

```text
真正调用 ChatGPT Image Tool 或其他 Image Tool
真正查看 Artifact Pixel
生成真实 Semantic Visual Result
```

本地 Python Package 无法自行访问 ChatGPT 产品内部的图片 Tool。alpha.26 提供完整的安全交接契约和可运行 Host Loop，但实际 Tool Invocation 必须由宿主环境完成。

### 13. Production Gateway API

alpha.26 在 alpha.25 Gateway 上新增：

```text
GET  /v1/work?project={project}
GET  /v1/work/{project}/{work_id}
POST /v1/work/{project}/{work_id}/claim
GET  /v1/work/{project}/{work_id}/attachments/{attachment_id}
POST /v1/work/{project}/{work_id}/result
```

Gateway 继续要求：

- Bearer Authentication；
- Capability Authorization；
- POST Idempotency-Key；
- Exclusive Mutation 使用 Task Etag 与 Lease；
- Result 使用 Work Claim；
- No-store Response；
- Request Body Limit；
- Loopback 默认绑定；
- Remote Bind 必须显式启用 TLS。

Image Result 使用 Raw Bytes，避免 Base64 Expansion。Visual Result 使用 UTF-8 JSON。

### 14. Runtime API

新增主要接口：

```python
runtime.list_host_work(...)
runtime.get_host_work(...)
runtime.claim_host_work(...)
runtime.get_host_work_attachment(...)
runtime.complete_host_image_work(...)
runtime.prepare_visual_inspection_work(...)
runtime.complete_host_visual_work(...)
```

`operation_summary()` 新增：

```text
host_work_count
available_host_work_count
claimed_host_work_count
completed_host_work_count
host_work
```

### 15. Signed Operation Evidence

以下操作进入 alpha.25 的 Private Operation Ledger：

```text
host.work.claim
host.work.image.complete
host.work.visual.complete
```

Ledger 不保存：

```text
Bearer Token
Task Lease Token
Work Claim Token
Raw Image Bytes
Credential Verifier
```

它保存脱敏 Request、Actor、Scope、Result Summary、Hash Chain 和 HMAC Signature。

### 16. 私有数据边界

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
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

框架 Git 只保存：

```text
Code
Schema
Generic Documentation
Wholly Fictional Fixtures
Contract Tests
```

框架 Git 不保存：

```text
真实用户 Theme
真实项目视觉规则
用户对话设计决策
真实 Prompt / Finding / Revision
用户图片或 Artifact
Host Credential / Claim / Runtime Evidence
```

### 17. 兼容性

alpha.26 保留：

- `submit_tool_result()` Legacy Path；
- `submit_authenticated_tool_result()` Production Callback；
- alpha.25 Gateway Endpoint；
- `guif-ops` 与 `guif-ledger`；
- Configurable Tool Adapter；
- Explicit `dry-run` Contract Test；
- Project、Workspace 与 Task Tool Override。

新流程优先使用 Host Work Contract。Legacy API 不自动获得 Claim、Attachment 和 Host Work Lifecycle Guarantee。

### 18. 已验证能力

alpha.26 Test 覆盖：

- Handoff 自动形成 Image Work；
- Embedded Host Loop 登记真实图片 Artifact；
- Image Result 后自动创建 Visual Work；
- 默认 `chatgpt-vision` Result 使 Artifact 通过；
- Visual Pass 更新 Aggregate QA 与 Export Gate；
- Review Finding 自动创建 Revision Job；
- Revision Approval 仍然独立且 Pending；
- Claim 不能由另一 Actor 使用；
- Gateway 可发现与领取 Work；
- 持久化 Work 不包含原始 Claim Secret。

### 19. 当前限制

- ChatGPT 产品侧必须嵌入 `ChatGPTHostLoop` 或消费 Gateway Work Endpoint；仓库无法自行接入 ChatGPT 内部 Tool Runtime；
- 默认 Semantic Inspector 是经过认证的 External Result Contract，不是本地自主 Vision Model；
- Work Claim 与 Task Lease 是 File-backed 本地协调，不是分布式一致性锁；
- 内置 WSGI Server 是单节点 Host Boundary，不是互联网 Edge Proxy；
- Private Storage 尚无 Encryption at Rest、Remote Sync、Retention Policy 和 Multi-device Conflict Resolution；
- Remote Git Push、PR 创建、Protected Branch 协商与 Server Check 尚未自动化；
- Current-tree Privacy Audit 无法证明历史 Commit、Fork、Cache 或外部 Clone 已清理。

### 20. alpha.27 下一阶段

下一阶段锁定为：

> **Conversation-first User Workflow and Recovery**

目标：

```text
一键初始化
Conversation Session State
新对话自动 Theme 确认
历史 Theme 选择 / 创建 / 派生
Project 选择
用户只描述页面或修改目标
自动展示生成、检查、修图和导出进度
失败 Work 可恢复、重试或取消
Private Backup
Schema Migration
不向普通用户暴露 Task ID / Etag / Lease / Claim / Callback ID
```

alpha.27 不新增大型生产子系统，重点是把 alpha.26 已经可运行的真实图片闭环包装成日常可用的对话式流程。

---

## English Version

### 0. Purpose

This living specification defines GUIF's product boundary, verified alpha.26 capabilities, privacy and security rules, failure behavior, compatibility, current limitations, and next phase. Features, tests, CI, bilingual READMEs, package metadata, and this specification must remain synchronized in the same release.

### 1. Product definition

GUIF is a local-first executable AI work framework for end-to-end game UI production, with natural language as the primary entry point and configurable Hosts and Tools.

GUIF Core governs:

```text
Project / Theme / Conversation Context
Planning / Direction / Contract / Prompt
Approval / Tool Routing / Work Coordination
Artifact / Provenance / Review / Revision
Export / Rollback / Git Change / Audit
```

Actual image generation, image editing, and semantic visual understanding are performed by configured Host-side Tools. Defaults are:

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

These are replaceable defaults, not hard-coded Core dependencies.

### 2. Alpha.26 production path

```text
confirm private Theme for the conversation
  -> Planner / Director / Resource / Prompt IR
  -> Contract QA
  -> Initial Approval Gate
  -> Tool Resolver
  -> chatgpt-image Handoff
  -> Private Host Work: image-generation or image-editing
  -> Authenticated Claim + Task Etag + Exclusive Lease
  -> Host invokes the real image Tool
  -> Authenticated Result Submission
  -> Artifact Registry
  -> Eligibility + File Identity + Metadata Review
  -> Private Host Work: visual-inspection
  -> chatgpt-vision Semantic Result
       -> passed
       -> review-required
       -> blocked
  -> actionable Findings create a Revision Plan and Revision Job
  -> Independent Revision Approval
  -> Controlled Editing Loop
  -> Gated Export
  -> Git Change Set / Commit / Revert
```

### 3. Product principles

1. A Theme is private, user-owned, versioned long-term data outside framework Git.
2. ChatGPT is the default visual production Host, but Hosts and Tools remain configurable.
3. GUIF never fabricates image pixels or presents a dry-run receipt as an image.
4. Metadata review never claims theme, composition, readability, or usability success.
5. Semantic visual conclusions require an explicit Visual Inspector Result.
6. Missing production capabilities enter recoverable waiting states; they never silently fall back to `dry-run`.
7. Host mutations are bound to authenticated Actors, Capabilities, Task Etags, and required Leases.
8. Work Claims, Task Leases, callbacks, and results bind the same Project, Task, Actor, and Credential.
9. Source Artifacts, References, and Attachments are revalidated for confinement, existence, and SHA-256 identity.
10. Initial Approval does not authorize later Revision work.
11. A replacement supersedes its source only after passing visual review.
12. Private Theme, Prompt, Work, Claim, Finding, and Runtime evidence stays outside the public repository by default.

### 4. Private Host Work

Alpha.26 adds a private claimable queue:

```text
<private-data-root>/host-work/<project>/work-*.json
```

Supported kinds:

```text
image-generation
image-editing
visual-inspection
```

Lifecycle:

```text
available -> claimed -> completed
```

Expired claims return to `available`. Completed work cannot be reclaimed or silently repeated.

Each record carries stable Project, Task, Handoff, Tool, Artifact, Request, Attachment, Submission Contract, Claim, Result, and timestamp evidence.

### 5. Work claims

Claiming requires an active Host credential with `host-work:claim`. GUIF returns a one-time token:

```text
guifw1.<work-id>.<secret>
```

Only its SHA-256 is persisted. The claim binds actor, credential, acquisition time, expiration time, and TTL. Invalid identity, actor mismatch, credential mismatch, expired tokens, or unavailable work fail closed.

### 6. Immutable attachments

Editing and inspection work may expose immutable Attachment descriptors. Each attachment includes scope, relative path, MIME, size, role, and SHA-256.

Before returning bytes, GUIF verifies path confinement, file existence, regular-file status, current SHA-256, and claim ownership. A Host therefore receives the exact approved source or review target, not a similarly named replacement.

### 7. Image completion

Image completion requires:

```text
host-work:complete
tool-result:submit
valid Work Claim
active Task Lease
matching Task Etag
non-empty bytes
filename and MIME
```

The result passes through the authenticated callback contract, creates a real non-simulation Artifact, preserves provenance, and automatically runs deterministic eligibility and image metadata checks. A passing metadata check creates visual-inspection work.

### 8. Semantic inspection

The default Inspector ID is `chatgpt-vision`. A visual result must be one of:

```text
passed
review-required
blocked
```

Review dimensions include theme consistency, hierarchy, content correctness, readability, usability, and resource compliance. Only an authenticated result may claim a semantic conclusion.

Actionable Findings produce a deterministic Revision Plan and an approval-pending Revision Job. No edit runs until the separate Revision Approval passes.

### 9. Embeddable Host SDK

`ChatGPTHostLoop` coordinates discovery, Task Etags, Leases, Claims, Attachment retrieval, result submission, Artifact registration, visual work preparation, and failure-safe lease release.

The Host supplies:

```text
image_executor(work, attachments)
visual_inspector(work, attachments)
```

Those callables perform the actual ChatGPT image/vision invocation. The local package cannot call ChatGPT's internal product tools by itself.

### 10. Gateway API

New endpoints:

```text
GET  /v1/work?project={project}
GET  /v1/work/{project}/{work_id}
POST /v1/work/{project}/{work_id}/claim
GET  /v1/work/{project}/{work_id}/attachments/{attachment_id}
POST /v1/work/{project}/{work_id}/result
```

Bearer authentication, Capability authorization, POST idempotency, Task Etag, Task Lease, Work Claim, request limits, no-store responses, loopback defaults, and TLS requirements remain enforced.

### 11. Runtime API

```python
runtime.list_host_work(...)
runtime.get_host_work(...)
runtime.claim_host_work(...)
runtime.get_host_work_attachment(...)
runtime.complete_host_image_work(...)
runtime.prepare_visual_inspection_work(...)
runtime.complete_host_visual_work(...)
```

Host work claims and completions are written to the private signed Operation Ledger without storing tokens or raw image bytes.

### 12. Privacy boundary

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
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

The public framework repository contains code, schemas, generic documentation, contract tests, and wholly fictional fixtures only.

### 13. Compatibility

Alpha.26 preserves legacy submission APIs, alpha.25 Gateway endpoints, configurable Tool Adapters, explicit dry-run testing, and Project/Workspace/Task overrides. The Host Work contract is the preferred production path and provides additional claim, attachment, and lifecycle guarantees.

### 14. Verified acceptance

Tests verify image work synthesis, real Artifact registration, automatic visual work creation, authenticated semantic passes, aggregate QA/export gating, automatic Revision Job construction, independent Revision Approval, actor-bound claims, Gateway discovery/claiming, and non-persistence of raw claim secrets.

### 15. Limitations

- ChatGPT must embed the Host SDK or consume Gateway work endpoints; the repository cannot self-connect to ChatGPT's internal tool runtime.
- The default semantic inspector is an authenticated external result contract, not a bundled local vision model.
- Claims and Leases are file-backed local coordination, not distributed consensus locks.
- The built-in WSGI server is a single-node Host boundary, not an internet-edge proxy.
- Private storage lacks encryption at rest, remote synchronization, retention policy, and multi-device conflict management.
- Remote Git push, PR creation, protected-branch negotiation, and server-check orchestration are not automated.
- Current-tree privacy audit cannot prove removal from historical commits, forks, caches, or external clones.

### 16. Alpha.27

The next phase is **Conversation-first User Workflow and Recovery**: one-command initialization, conversation session state, automatic Theme confirmation, Project selection, user-facing generation/revision progress, resumable failed work, private backup and schema migration, and a workflow that hides Task IDs, Etags, Leases, Claims, and Callback IDs from ordinary users.
