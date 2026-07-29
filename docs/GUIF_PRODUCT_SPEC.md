# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.28`  
> Public API / 公共 API: `1`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF 的产品定位、alpha.28 已验证能力、冻结的 MVP 范围、隐私和安全边界、失败策略、兼容性、验收标准与下一阶段。Feature、Test、CI、中英文 README、Version Metadata 与本规格必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、自然语言优先、Host 与 Tool 均可配置、面向游戏 UI 全生产流程的可执行 AI 工作框架。

GUIF Core 负责：

```text
Project / Private Theme / Conversation Context
Planning / Direction / Contract / Prompt IR
Approval / Tool Routing / Host Work Coordination
Artifact / Provenance / Metadata Review / Semantic Review
Revision / Supersession / Export / Rollback / Git Change
Private Backup / Migration / Diagnostics / Recovery / Audit
```

真实图片生成、图片修改和语义视觉理解由经过配置的 Host 与 Tool 执行。默认组合：

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

以上均为默认契约，不是不可替换的 Core 依赖。

### 2. alpha.28 产品目标

alpha.28 不新增大型产品域，而是冻结 alpha.27 的日常 MVP，补齐进入 Beta 前必须存在的可靠性能力：

```text
一条命令完成初始化
Conversation-first 默认入口
Private Theme 确认
自然语言需求幂等提交
Initial / Revision Contextual Approval
Task-scoped ChatGPT Host Work
真实 Image / Edit / Vision Result
Gated Export
Private Backup / Verify / Plan-first Restore
Recorded Private Schema Migration
Privacy-safe Diagnostics
End-to-end Acceptance Gate
Public Compatibility Contract
```

### 3. 默认生产路径

```text
guif-ready start
  -> Project 初始化或复用
  -> ChatGPT Host Credential 创建或验证
  -> Private Conversation Record
  -> Theme confirmation
  -> Natural-language Request
  -> Planner / Director / Resource / Prompt IR
  -> Contract QA
  -> Initial Approval
  -> Tool Resolver
  -> image-generation Host Work
  -> Real Image Result
  -> Artifact Registry
  -> Deterministic Metadata Review
  -> visual-inspection Host Work
  -> Semantic Result
       -> passed
       -> review-required
       -> blocked
  -> Actionable Finding 形成 Revision Plan / Revision Job
  -> Independent Revision Approval
  -> image-editing Host Work
  -> Replacement Review
  -> Review-gated Supersession
  -> Gated Export
  -> Git Change Set / Commit / Revert
```

### 4. 核心产品原则

1. Theme 是用户拥有的私有、可版本化长期数据，不属于框架 Git；
2. ChatGPT 默认执行图片生成、修图和视觉理解，但 Host 与 Tool 可配置；
3. GUIF 不伪造 Pixel，也不把 Dry-run Receipt 当成图片；
4. Metadata Review 不能声明 Theme、构图、可读性或可用性通过；
5. 语义视觉结论必须来自明确的 Visual Inspector Result；
6. 生产任务缺少 Tool 时进入可恢复等待状态，不静默回退到 `dry-run`；
7. Initial Approval 不自动授权 Revision；
8. Replacement 只有通过最终视觉审查后才能 Supersede Source；
9. Conversation 默认视图不暴露底层 Runtime Identity；
10. Bearer、Lease、Claim 等 Secret 只在必要边界出现，不写入公共或普通用户视图；
11. Private Backup 默认不包含 Host Credential 与 Ledger Signing Key；
12. Restore 默认只生成计划，必须显式 `apply`；
13. 未知未来 Schema、无效记录和 Raw Secret Field Fail Closed；
14. Breaking Change 必须增加 Public API Version 并提供迁移路径；
15. 公共仓库示例只使用完全虚构的 Fixture。

### 5. Frozen Conversation MVP

Public API Version：

```text
1
```

冻结的用户 Stage：

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
completed
recoverable-error
cancelled
attention-required
```

冻结的用户 Action：

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
export
recover
retry
```

beta.1 必须保持以上名称与语义。破坏性变化要求新的 Public API Version。

### 6. One-command Bootstrap Contract

命令：

```bash
guif-ready start \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

行为：

```text
若 Project 不存在，则创建标准 Project 结构
若未提供 GUIF_HOST_TOKEN，则签发 ChatGPT Host Credential
创建或打开 Private Conversation Record
返回 Theme Confirmation 或当前 Conversation Stage
```

新 Bearer Token 只显示一次。Bootstrap 不将 Token 写入：

```text
Project Git
Conversation Record
Diagnostics
Backup Manifest
Operation Summary
```

### 7. Conversation View Contract

默认用户 View 至少包含：

```text
schema_version
conversation_id
project
stage
message
theme summary
actions
safe Artifact summaries
recovery summary
updated_at
```

默认不得包含：

```text
Task ID / Task Etag
Approval ID / Revision ID
Lease Token / Claim Token
Work ID / Handoff ID / Callback ID
Bearer Token
Private Storage Path
Raw Theme Content
```

显式 Diagnostics 可提供必要开发信息，但 Secret 仍不得持久化或返回。

### 8. Private Theme Contract

新 Conversation 在没有 Conversation-level Binding 时必须进入 `theme-confirmation`。

允许路径：

```text
选择历史 Theme
创建新 Theme
派生不可变新版本
明确本次不绑定 Theme
```

真实 Theme Content 存储在：

```text
<private-data-root>/themes/
```

Conversation 与 Project 只保存 Opaque Theme Reference 和 Snapshot Hash。

### 9. Approval 与 Revision

Initial Approval 只授权当前 Prompt Job。

Semantic Finding 产生 Revision 后：

```text
Revision Plan
-> Versioned Revision Job
-> revision-approval-required
-> Approved
-> image-editing Work
```

Source Artifact 在 Replacement 通过前继续 Active。Simulation、Non-visual、Lineage Invalid 或 Semantic Review 未通过的 Replacement 不得 Supersede Source。

### 10. Host Work 与 Tool Contract

支持：

```text
image-generation
image-editing
visual-inspection
```

Host Work 需要：

```text
Authenticated Actor
Capability Authorization
Task-scoped Discovery
Task Etag
Exclusive Lease
Actor-bound Claim
Immutable Attachments
Result Contract
```

`ChatGPTHostLoop` 可嵌入 Host 环境。Local Package 本身不能调用 ChatGPT Internal Image Tool。

### 11. Artifact 与 Review Contract

真实图片 Artifact 必须：

```text
visual = true
simulation = false
supported MIME
file exists under allowed root
SHA-256 matches
actual dimensions and format verified
Output Contract satisfied
```

Metadata Review 通过后只进入 `not-run` Semantic State，不能伪造视觉通过。

Semantic Result 允许：

```text
passed
review-required
blocked
```

### 12. Portable Private Backup

默认 Profile：

```text
portable
```

包含：

```text
themes
conversation-theme-bindings
conversation-workflows
project-theme-bindings
runs
plans
host-work
migrations
privacy-reports
```

排除：

```text
host-credentials
operation-ledger
operation-audit
gateway-requests
backups
diagnostics
```

排除原因：默认 Portable Archive 不应携带 Credential Verifier、Signing Key 或操作认证材料。

### 13. Full-local Backup

`full-local` 只有在显式 `include_sensitive=True` 或 CLI `--include-sensitive` 时允许创建。

该 Archive 可能包含：

```text
Credential Verifier
Ledger Signing Key
Authenticated Operational Evidence
```

GUIF 当前只提供完整性，不提供 Archive Encryption。Sensitive Archive 必须放入受保护的加密存储。

### 14. Backup Manifest 与 Verification

Backup Manifest 至少包含：

```text
schema_version
created_at
created_by_release
profile
sensitive_material_included
categories
file_count
total_size_bytes
files[path, archive_member, sha256, size_bytes]
manifest_sha256
encryption
restore_requires_explicit_apply
```

Verification 必须检查：

```text
Canonical Member Path
No Absolute Path / Traversal
No Duplicate Member
No Symbolic Link
Manifest Hash
Per-file SHA-256 / Size
Total Extraction Limit
No Unmanifested Member
```

### 15. Plan-first Restore

Restore 默认：

```text
apply = false
```

Conflict Policy：

```text
fail
skip
replace
```

`replace` 在存在冲突时默认先创建 Portable Pre-restore Backup。

应用 Restore 时：

```text
Verified Archive
-> Plan
-> Explicit Apply
-> Atomic Temporary Write
-> Replace
-> Post-write SHA-256 Verification
```

### 16. Private Schema Migration

alpha.28 保持 Conversation Workflow Schema Version `1` 兼容。

Migrator 可补齐：

```text
status
continue_unbound
active_task_id
request_records
checkpoint
history
privacy metadata
compatibility metadata
migration_history
```

Migrator 不静默处理：

```text
Unsupported Future Schema
Invalid JSON
Non-object Record
Raw Bearer / Lease / Claim Secret Fields
```

每次 Apply 必须写入 Private Migration Report。

### 17. Privacy-safe Diagnostics

Diagnostics 检查：

```text
Project Contract
Private Storage Writable
Private Schema State
Operation Ledger Integrity
Host Credential Capabilities
Conversation State
Portable Backup Presence
Compatibility Contract
```

默认 Report 不含底层 ID、Secret 或 Private Root Path。持久化位置：

```text
<private-data-root>/diagnostics/<project>/
```

### 18. Acceptance Gate

默认通过条件：

```text
blocked readiness checks = 0
and
Conversation stage in {ready-to-export, completed}
```

Strict 条件：

```text
--require-completed
=> Conversation stage = completed
```

Acceptance 不调用 Fake Image Model，也不把 Metadata-only Artifact 视为 Visual Pass。

### 19. Compatibility Policy

alpha.28 到 beta.1：

```text
Frozen Conversation Facade backward-compatible
Private Schema change requires detection and migration
Breaking user-facing change requires new Public API Version
Legacy ProviderAdapter remains explicit compatibility mode
Dry-run remains explicit test/development mode
```

### 20. Private Data Layout

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  conversation-workflows/
  project-theme-bindings/
  host-credentials/
  host-work/
  gateway-requests/
  operation-audit/
  operation-ledger/
  backups/
  diagnostics/
  runs/
  plans/
  migrations/
  privacy-reports/
```

以上默认位于 Framework Git 与 Project Git 之外。

### 21. Failure Strategy

```text
Missing Theme                 -> theme-confirmation
Missing Tool                  -> tool-configuration-required
External Result Pending       -> image-production / visual-review
Pipeline Failure              -> recoverable-error
Approval Rejected             -> changes-required
Revision Approval Pending     -> revision-approval-required
Backup Integrity Failure      -> restore blocked
Restore Conflict              -> plan blocked unless skip/replace
Unsupported Private Schema    -> migration blocked
Ledger Integrity Failure      -> authenticated mutation fail closed
```

### 22. alpha.28 验收标准

```text
[ ] One-command Bootstrap creates or reuses Project safely
[ ] Token shown once and not persisted in Conversation
[ ] Theme confirmation remains mandatory unless explicitly unbound
[ ] Normal user View hides Runtime identities
[ ] Real image and semantic review loop remains functional
[ ] Revision Approval remains independent
[ ] Portable Backup excludes credentials and signing keys
[ ] Backup tampering is detected
[ ] Restore is plan-first and conflict-safe
[ ] Supported private repairs are recorded
[ ] Raw secret-like fields block migration
[ ] Diagnostics are privacy-safe
[ ] Acceptance reaches ready-to-export without manual Runtime IDs
[ ] Public API Version and frozen Stage/Action contract are published
[ ] Python 3.10 / 3.11 / 3.12 CI passes
[ ] English README, Chinese README, version metadata, tests and spec are synchronized
```

### 23. 当前限制

- Repository 无法自行进入 ChatGPT 产品内部调用图片 Tool；
- Backup Archive 未加密；
- File-backed Lease 与 Claim 不是 Distributed Consensus；
- WSGI Gateway 不是 Internet Edge Proxy；
- Remote Private Sync、Retention、Key Rotation 与 Multi-device Conflict 尚未实现；
- Current-tree Privacy Audit 无法证明 Git History、Fork、Cache 或 Clone 已清理；
- Remote Git Release Orchestration 仍位于 Local Core 之外。

### 24. 下一阶段

下一目标为 `beta.1`，不扩张冻结 MVP，只进行生产加固：

```text
Encrypted Backup Integration Boundary
Upgrade Tests from supported Alpha versions
Failure Injection / Performance / Long-run Tests
Packaged Installation
Release Notes and Support Window
Security Review and Key Rotation Guidance
```

---

## English Version

### 0. Purpose

This document defines GUIF's product position, verified alpha.28 capabilities, frozen MVP scope, privacy and security boundaries, failure strategy, compatibility contract, acceptance criteria, and next phase. Features, tests, CI, both READMEs, package version metadata, and this specification must remain synchronized in one release.

### 1. Product Definition

GUIF is a local-first, natural-language-first, configurable Host and Tool framework for end-to-end game UI production.

GUIF Core owns:

```text
Project / Private Theme / Conversation Context
Planning / Direction / Contract / Prompt IR
Approval / Tool Routing / Host Work Coordination
Artifact / Provenance / Metadata Review / Semantic Review
Revision / Supersession / Export / Rollback / Git Change
Private Backup / Migration / Diagnostics / Recovery / Audit
```

Default replaceable contracts:

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

### 2. Alpha.28 Goal

Alpha.28 freezes the alpha.27 daily-use MVP and adds the reliability contracts required before beta:

```text
one-command bootstrap
conversation-first default path
private Theme confirmation
idempotent natural-language requests
contextual Initial and Revision approval
Task-scoped ChatGPT Host work
real image/edit/vision results
Gated Export
verified private backup and plan-first restore
recorded private schema migration
privacy-safe diagnostics
end-to-end acceptance gate
public compatibility contract
```

### 3. Frozen Public Contract

Public API version:

```text
1
```

Beta.1 must preserve the published conversation stages and actions. A breaking change requires a new public API version and an explicit migration path.

### 4. Bootstrap

`guif-ready start` creates or reuses the Project, validates or issues the ChatGPT Host credential, and opens the private Conversation. A new Bearer token is visible once and is never persisted in Project Git or the Conversation record.

### 5. Private Theme

A Conversation without a Conversation-level Theme binding must enter `theme-confirmation`. The user may select history, create a Theme, derive an immutable version, or explicitly continue unbound. Real Theme content remains outside framework and Project Git.

### 6. Conversation View

The default view contains the current user-facing stage, message, private Theme summary, contextual actions, safe Artifact summaries, and recovery status. It excludes Task IDs, etags, Approval IDs, Revision IDs, leases, claims, Handoffs, callbacks, Bearer tokens, private paths, and raw Theme content.

### 7. Real Tool Boundary

GUIF coordinates authenticated, Task-scoped Host Work. It does not fabricate pixels and cannot invoke ChatGPT's internal image tool from the local package. Semantic visual conclusions require an authenticated inspector result; metadata alone is never a semantic pass.

### 8. Revision Safety

Initial Approval does not authorize editing. A replacement may supersede its source only after real visual output, valid lineage, deterministic metadata checks, and passing semantic review.

### 9. Backup Profiles

`portable` includes private Themes, bindings, Conversation records, Runs, Plans, Host Work, migrations, and privacy reports. It excludes credentials, credential verifiers, operation-ledger signing keys, Gateway receipts, and operation-audit authentication material.

`full-local` requires explicit sensitive-material consent. GUIF archives are integrity checked but not encrypted at rest.

### 10. Verification and Restore

Verification rejects path traversal, absolute or non-canonical paths, duplicates, symbolic links, size/hash mismatches, excessive extraction size, and unmanifested members.

Restore is plan-only by default. Explicit apply supports `fail`, `skip`, and `replace`. Replace creates a portable pre-restore backup by default, writes atomically, and verifies SHA-256 after materialization.

### 11. Private Migration

Alpha.28 preserves Conversation Workflow schema version 1 while repairing missing frozen-MVP metadata. Unsupported future schemas, invalid JSON, and raw secret-like fields fail closed. Every applied repair is recorded.

### 12. Diagnostics and Acceptance

Privacy-safe diagnostics inspect Project validity, private storage, private schema state, operation-ledger integrity, credential capabilities, Conversation recovery, backup presence, and compatibility. Default reports do not expose low-level IDs, secrets, or private roots.

The acceptance gate passes only when no blocking readiness check exists and the Conversation is `ready-to-export` or `completed`. Strict mode requires `completed`.

### 13. Private Layout

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  conversation-workflows/
  project-theme-bindings/
  host-credentials/
  host-work/
  gateway-requests/
  operation-audit/
  operation-ledger/
  backups/
  diagnostics/
  runs/
  plans/
  migrations/
  privacy-reports/
```

### 14. Limitations

The repository cannot invoke ChatGPT internal tools by itself; backup encryption, distributed coordination, remote private sync, retention, key rotation, multi-device conflict resolution, internet-edge proxying, and remote Git release orchestration are not included in alpha.28.

### 15. Next Phase

`beta.1` hardens the frozen MVP through encrypted-backup integration boundaries, supported-version upgrade tests, failure injection, performance and long-run tests, packaged installation, release notes, support-window commitments, and security guidance.
