# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-beta.1`  
> Package / 包版本: `1.0.0b1`  
> Public API / 公共 API: `1`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF beta.1 的产品定位、冻结的 Conversation MVP、默认生产路径、Host / Tool 契约、私有数据边界、备份保护、升级保障、故障注入、稳定性检查、兼容与支持策略、验收标准和已知限制。

Feature、Test、CI、中英文 README、Package Version、Release Notes、Security Review 与本规格必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、自然语言优先、Host 与 Tool 均可配置、面向游戏 UI 全生产流程的可执行 AI 工作框架。

GUIF Core 负责：

```text
Project / Private Theme / Conversation Context
Planning / Direction / Contract / Prompt IR
Approval / Tool Routing / Host Work Coordination
Artifact / Provenance / Metadata Review / Semantic Review
Revision / Supersession / Export / Rollback / Git Change
Private Backup / Protection Boundary / Migration / Recovery
Diagnostics / Upgrade Assurance / Soak / Audit
```

真实图片生成、图片修改和语义视觉理解由经过配置的 Host 与 Tool 执行。默认组合：

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

以上均为默认契约，不是不可替换的 Core 依赖。

### 2. beta.1 目标与范围冻结

beta.1 不新增普通用户产品域，不改变 alpha.28 冻结的 Public API Version `1`，而是补齐生产加固能力：

```text
External Backup Protection Boundary
Supported alpha.27 / alpha.28 Upgrade Assurance
Explicit Fault Injection Gate
Bounded Repeatability / Latency Soak
Wheel + Source Distribution Build / Install Verification
Release Notes / Security Review / Support Window
```

正常用户仍沿用：

```text
开始 Conversation
-> 确认、创建、派生或明确跳过 Private Theme
-> 自然语言需求
-> Initial Approval
-> 真实图片生成
-> Metadata Review
-> Semantic Visual Review
-> 必要时 Independent Revision Approval
-> 真实图片编辑
-> Review-gated Supersession
-> Gated Export
```

### 3. 核心产品原则

1. Theme 是用户拥有的私有、可版本化长期数据，不属于 Framework Git 或 Project Git；
2. 对话开始时必须确认 Theme，可选择历史 Theme、创建、派生或明确不绑定；
3. ChatGPT 默认执行图片生成、修图和视觉理解，但 Host 与 Tool 均可配置或替换；
4. GUIF 不伪造 Pixel，不把 Dry-run Receipt 当成图片；
5. Metadata Review 不能声明 Theme、构图、可读性或可用性通过；
6. 语义视觉结论必须来自明确的 Visual Inspector Result；
7. 生产任务缺少 Tool 时进入可恢复等待状态，不静默回退到 `dry-run`；
8. Initial Approval 不自动授权 Revision；
9. Replacement 只有通过最终视觉审查后才能 Supersede Source；
10. Conversation 默认视图不暴露底层 Runtime Identity 或 Private Path；
11. Bearer、Lease、Claim、Signing Key 等 Secret 不写入公共输出；
12. Portable Backup 默认排除 Host Credential Verifier 与 Ledger Signing Key；
13. Restore 默认只生成计划，必须显式 Apply；
14. GUIF 不实现自定义加密算法，不对外部加密工具的强度作虚假保证；
15. External Protection 缺少配置时 Fail Closed，不回退到未保护复制；
16. 未知 Source Release、未来 Schema、无效记录和 Raw Secret Field Fail Closed；
17. Breaking Change 必须增加 Public API Version 并提供迁移路径；
18. 公共仓库示例与测试只使用完全虚构的 Fixture。

### 4. Frozen Conversation MVP

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

Compatibility Contract 为保持既有字段语义，继续返回：

```text
release: 1.0.0-alpha.28
```

并新增：

```text
current_release: 1.0.0-beta.1
origin_release: 1.0.0-alpha.28
channel: beta
```

### 5. Conversation View 与隐私契约

默认 View 至少包含：

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
Bearer Token / Signing Key
Private Storage Path
Raw Theme Content
Artifact Bytes
```

显式开发 Diagnostics 可提供必要定位信息，但 Secret 仍不得返回或持久化。

### 6. Private Theme Contract

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

Framework Git 只允许代码、Schema、通用文档和虚构 Fixture。

### 7. Host Work 与真实图片契约

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
Idempotent Submission
```

`ChatGPTHostLoop` 可嵌入 ChatGPT 或其他 Host 环境。Local Python Package 本身不能进入 ChatGPT 产品内部调用 Image Tool。

真实图片 Artifact 必须满足：

```text
visual = true
simulation = false
supported MIME
file under allowed root
SHA-256 matches
actual dimensions / format verified
Output Contract satisfied
```

Metadata Review 通过后只进入 `not-run` Semantic State。Semantic Result 允许：

```text
passed
review-required
blocked
```

### 8. Approval、Revision 与 Export

Initial Approval 只授权当前 Prompt Job。

Semantic Finding 产生 Revision 后：

```text
Revision Plan
-> Versioned Revision Job
-> revision-approval-required
-> Approved
-> image-editing Work
-> Replacement Semantic Review
-> Review-gated Supersession
```

Source Artifact 在 Replacement 通过前继续 Active。Simulation、Non-visual、Lineage Invalid 或 Semantic Review 未通过的 Replacement 不得 Supersede Source。

Gated Export 必须保持：

```text
Contract QA passed
Active visual Artifacts semantically passed
Authenticated export capability
Exclusive Task Lease
Engine manifest / transaction evidence
Rollback and Git Change controls
```

### 9. Portable 与 Full-local Backup

Portable Profile 包含：

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

Portable Profile 排除：

```text
host-credentials
operation-ledger
operation-audit
gateway-requests
backups
diagnostics
upgrade-reports
hardening-reports
```

`full-local` 只有显式 `include_sensitive=True` 或 CLI `--include-sensitive` 时允许创建。它可能包含 Credential Verifier、Signing Key 与 Authenticated Operational Evidence。

未保护 GUIF Archive 只提供完整性，不提供静态加密。

### 10. Backup Verification 与 Plan-first Restore

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
No Duplicate / Unmanifested Member
No Symbolic Link / Directory Member
Manifest Hash
Per-file SHA-256 / Size
Total Extraction Limit
```

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

`replace` 默认先创建 Portable Pre-restore Backup。应用流程：

```text
Verified Archive
-> Plan
-> Explicit Apply
-> Atomic Temporary Write
-> Replace
-> Post-write SHA-256 Verification
```

### 11. External Backup Protection Boundary

GUIF beta.1 提供外部备份保护集成边界，不实现自定义密码学。

环境配置：

```text
GUIF_BACKUP_PROTECTOR_ID
GUIF_BACKUP_PROTECT_COMMAND_JSON
GUIF_BACKUP_UNPROTECT_COMMAND_JSON
GUIF_BACKUP_PROTECT_TIMEOUT_SECONDS
```

Command 必须是 JSON argv Array，并包含：

```text
{input}
{output}
```

执行规则：

```text
subprocess argv
shell = false
bounded timeout
explicit configuration only
no unprotected fallback
non-empty regular output required
existing destination / receipt rejected
atomic temporary publication
```

Protection Receipt 只允许保存：

```text
schema_version
status
adapter_id
source filename / size / SHA-256
protected filename / size / SHA-256
created_at
secret_material_persisted = false
command_persisted = false
```

不得保存：

```text
Command argv
stdout / stderr
Passphrase / Key
Secret Environment Value
Bearer / Lease / Claim
```

Receipt 提供本地完整性证据，不等同于数字签名。可同时重写 Protected File 与 Receipt 的攻击者仍可伪造替代证据。长期真实性应依赖外部签名、加密或不可变备份系统。

新命令：

```text
guif-ready backup-protect
guif-ready backup-protection-verify
guif-ready backup-unprotect
```

加密算法、Key Custody、Rotation、Recovery 与外部程序安全性由操作方和外部 Tool 负责。

### 12. Supported Alpha Upgrade Assurance

直接支持 Source Release：

```text
1.0.0-alpha.27
1.0.0-alpha.28
```

Target：

```text
1.0.0-beta.1
```

默认 Upgrade Gate：

```text
Explicit Source Release
-> Supported Source Check
-> Portable Backup Required
-> Private Schema Scan
-> Block Unknown Schema / Raw Secret Field
-> Explicit Apply
-> Recorded Migration when needed
-> Post-migration Current Check
-> Public API Version 1 preserved
-> Private Upgrade Report
```

未知 Source Release 不自动推断，也不静默迁移。

公共 Upgrade Result 不返回 Private Report Path 或 Secret；完整 Evidence 保存在：

```text
<private-data-root>/upgrade-reports/
```

### 13. Fault Injection Contract

Fault Injection 只用于测试和开发，默认关闭。

环境驱动必须同时设置：

```text
GUIF_FAULT_POINTS=<named points>
GUIF_ALLOW_FAULT_INJECTION=1
```

只设置 `GUIF_FAULT_POINTS` 时必须报错，而不是启用故障。

beta.1 已定义的保护流程 Fault Point：

```text
backup-protection.before-publish
backup-protection.before-recovery-publish
```

故障测试必须证明：

```text
Original verified archive remains valid
No incomplete protected/recovered destination published
Temporary output removed
No silent retry or fallback
```

### 14. Bounded Soak 与性能证据

`HardeningService.soak()` 重复执行非变更型读取：

```text
Project validation
Private schema scan
Operation ledger verification
Non-persisting Conversation stage derivation
Optional backup verification
```

Iteration 范围：

```text
1..10000
```

Report 至少包含：

```text
iterations / successes / failures
sanitized error types / codes
total / mean / p50 / p95 / max timing
optional p95 threshold
observed public stages
mutating_operations_performed = false
production_state_mutated = false
```

Report 私有存储：

```text
<private-data-root>/hardening-reports/
```

Soak 不等同于完整负载测试、分布式一致性验证或 Host Tool SLA。

### 15. Packaged Installation Contract

CI 必须在 Python 3.10、3.11、3.12 上执行：

```text
install development dependencies
pytest
build wheel + source distribution
install generated wheel
verify guif.__version__ == 1.0.0b1
run guif-ready contract smoke test
```

正式包不得依赖未提交的本地文件或真实用户数据。

### 16. Support 与 Deprecation Contract

`guif-ready support` 与 `SUPPORT.md` 定义：

```text
Current beta supported until superseded
Previous beta security fixes for 30 days when practical
No hosted SLA
Supported direct upgrades: alpha.27 / alpha.28
Breaking change requires new Public API Version
Explicit migration path required
Silent private schema mutation forbidden
```

公开 Security Report 不得包含 Credential、Secret、真实 Theme、图片、Private Record 或 Backup Archive。

### 17. Private Data Layout

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
  upgrade-reports/
  hardening-reports/
  runs/
  plans/
  migrations/
  privacy-reports/
```

Protected Archive 和 Secret-free Receipt 应保存在 Workspace 之外的受保护位置，不作为 Framework Fixture。

### 18. 安全与失败策略

GUIF 对以下情况 Fail Closed：

```text
Missing / invalid Host Credential
Capability mismatch
Task Etag or Lease mismatch
Work Claim mismatch
Unknown Tool or incompatible Host
Metadata / Semantic Review failure
Invalid Artifact lineage
Unsafe backup member or restore target
Missing external protection configuration
Protection output collision or tampering
Unsupported upgrade source
Blocked private schema
Fault points configured without explicit allow flag
```

GUIF 不承诺：

```text
External encryption strength
External key recovery
Third-party Host / Tool availability
Distributed consensus
Internet-edge proxy security
Removal of previously published data from forks / caches
```

### 19. beta.1 验收标准

Release 必须满足：

```text
Public API Version remains 1
Frozen Conversation stages/actions preserved
Package version and docs synchronized
All public fixtures wholly fictional
No real Theme / Prompt / Image / Credential committed
External protection has no shell and no silent fallback
Protection round-trip and tamper rejection tested
Fault interruption leaves original archive valid
alpha.27 / alpha.28 upgrade path tested
Unsupported source upgrade rejected
Soak check performs non-mutating reads
Wheel and sdist build/install smoke tests pass
Python 3.10 / 3.11 / 3.12 CI pass
Release Notes / Security Review / Support Policy published
```

### 20. 已知限制与下一阶段

当前限制：

- GUIF 无法自行进入 ChatGPT 产品内部调用 Image Tool；
- GUIF 不评估外部加密算法强度，也不能恢复丢失 Key；
- File-backed Lease 与 Work Claim 是单节点协调；
- 内置 WSGI Gateway 不是 Internet-edge Reverse Proxy；
- Remote Private-data Sync、Retention Automation 与 Multi-device Conflict Resolution 尚未实现；
- Current-tree Privacy Audit 无法清除 Git History、Fork 或外部 Cache；
- Pillow `Image.getdata()` Deprecation Warning 尚未清理。

下一维护阶段保持 MVP 冻结，优先处理：

```text
Pillow deprecation maintenance
larger supported-upgrade fixture corpus
longer-duration soak evidence
external protection adapter examples without bundled secrets
release artifact provenance / signing boundary
bug fixes and compatibility maintenance
```

---

## English Version

### 0. Purpose

This document defines GUIF beta.1: the frozen Conversation MVP, default production path, Host/Tool contracts, private-data boundary, backup protection, upgrade assurance, fault injection, hardening checks, compatibility/support policy, acceptance criteria, and known limitations.

Features, tests, CI, both READMEs, package metadata, release notes, security review, and this specification must remain synchronized in each release.

### 1. Product Definition

GUIF is a local-first, natural-language-first executable AI framework for end-to-end game UI production with configurable Hosts and Tools.

GUIF Core owns:

```text
Project / Private Theme / Conversation Context
Planning / Direction / Contract / Prompt IR
Approval / Tool Routing / Host Work Coordination
Artifact / Provenance / Metadata Review / Semantic Review
Revision / Supersession / Export / Rollback / Git Change
Private Backup / Protection Boundary / Migration / Recovery
Diagnostics / Upgrade Assurance / Soak / Audit
```

Default replaceable contracts:

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

### 2. Beta.1 Scope

Beta.1 does not add a new normal-user product domain. It preserves public API version `1` and adds:

```text
External Backup Protection Boundary
Supported alpha.27 / alpha.28 Upgrade Assurance
Explicit Fault Injection Gate
Bounded Repeatability / Latency Soak
Wheel + Source Distribution Build / Install Verification
Release Notes / Security Review / Support Window
```

### 3. Immutable Product Principles

- Theme is private, user-owned, versioned data outside framework/project Git.
- A Conversation confirms, creates, derives, or explicitly skips Theme before production.
- ChatGPT image/vision capabilities are defaults, not hard-coded dependencies.
- GUIF never fabricates pixels or treats dry-run evidence as an image.
- Metadata review never claims semantic visual quality.
- Initial Approval never authorizes Revision.
- No silent production fallback to `dry-run` or unprotected backup copying.
- Normal views hide runtime identities, secrets, private paths, and raw Theme content.
- Unknown schemas, raw secret fields, unsupported releases, unsafe paths, and tampering fail closed.
- Breaking changes require a new public API version and explicit migration path.
- Public fixtures are wholly fictional.

### 4. Frozen Conversation Contract

Public API version: `1`.

Frozen stages and actions are exactly those listed in the Chinese section above and returned by `guif-ready contract`.

For backward compatibility:

```text
release: 1.0.0-alpha.28
current_release: 1.0.0-beta.1
origin_release: 1.0.0-alpha.28
channel: beta
```

### 5. Host, Artifact, Review, Revision, and Export

Production Host Work requires authenticated capability, task scope, etag, exclusive lease, actor-bound claim, immutable attachments, and a result contract.

A valid visual Artifact is real, non-simulation, located under an allowed root, and verified for SHA-256, MIME, dimensions, format, and output contract.

Semantic visual status is one of:

```text
passed
review-required
blocked
```

A source Artifact remains active until an independently approved, lineage-valid, real replacement passes semantic review. Gated Export never bypasses QA, lease, Engine transaction, rollback, or Git controls.

### 6. Backup and Restore

Portable backups include recoverable user production data and exclude credential verifiers, ledger signing keys, and authenticated operational material. Full-local backups require an explicit sensitive-material decision.

Archives are integrity checked through manifest and per-file evidence. Restore is plan-first and requires explicit apply. Replace mode creates a portable pre-restore backup by default, writes atomically, and re-verifies SHA-256.

### 7. External Backup Protection

GUIF supplies an integration boundary, not cryptography.

The external adapter:

```text
uses argv with shell=false
requires {input} and {output}
has a bounded timeout
requires explicit configuration
has no unprotected fallback
refuses existing destination / receipt
requires non-empty regular output
publishes atomically
persists only filename / size / SHA-256 evidence
```

It never persists command argv, stdout/stderr, passphrases, keys, or secret environment values.

The external program/operator owns algorithm selection, key custody, rotation, and recovery.

### 8. Upgrade Assurance

Supported direct source releases:

```text
1.0.0-alpha.27
1.0.0-alpha.28
```

The default gate requires a portable backup, scans private schemas, blocks unsupported/secret-bearing records, applies only recorded supported repairs, verifies current schemas, and preserves public API version `1`.

### 9. Fault Injection and Soak

Fault injection is disabled by default and requires both named points and `GUIF_ALLOW_FAULT_INJECTION=1`.

Soak checks repeat non-mutating Project, schema, ledger, Conversation-stage, and optional backup reads. Reports contain aggregate timings and sanitized errors only and remain private.

### 10. Packaging and Support

CI tests Python 3.10, 3.11, and 3.12, builds wheel/sdist, installs the wheel, verifies the package version, and runs a CLI contract smoke test.

The current beta is supported until superseded. When practical and safe, the previous beta may receive security fixes for 30 days. This is not a hosted SLA.

### 11. Acceptance

Beta.1 is acceptable only when the frozen public contract is preserved, privacy fixtures remain fictional, protection/upgrade/fault/soak tests pass, package artifacts install successfully, all Python matrix jobs pass, and synchronized release/security/support documentation is published.

### 12. Limitations

GUIF cannot invoke ChatGPT internal image tools by itself, assess external cryptographic strength, recover lost external keys, provide distributed consensus, act as an internet-edge proxy, synchronize private data across devices, or erase content already copied into Git history/forks/caches.

The next maintenance phase remains scope-frozen and focuses on deprecation cleanup, broader upgrade fixtures, longer soak evidence, safe external-adapter examples, release provenance boundaries, and compatibility-preserving bug fixes.
