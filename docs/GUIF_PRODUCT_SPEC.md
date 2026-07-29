# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-beta.2`  
> Package / 包版本: `1.0.0b2`  
> Public API / 公共 API: `1`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF beta.2 的产品定位、冻结的 Conversation MVP、真实图片与视觉契约、私有数据边界、备份与外部保护、升级保障、故障注入、非变更型稳定性检查、Release Artifact Hash Provenance、兼容策略、验收标准和已知限制。

Feature、Test、CI、中英文 README、Package Version、Release Notes、Security Review、Support Policy 与本规格必须在同一个 Release 中保持一致。

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
Release Artifact Hash Provenance
```

真实图片生成、图片修改和语义视觉理解由经过配置的 Host 与 Tool 执行。默认组合：

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

以上均为默认契约，不是不可替换的 Core 依赖。

### 2. beta.2 目标与最小完整范围

beta.2 不新增普通用户产品域，不改变 alpha.28 冻结的 Public API Version `1`，而是完成 Maintenance and Provenance Hardening：

```text
Pillow Image Pixel API Compatibility
Zero Known Pillow getdata Deprecation Warning in CI
Wheel / sdist SHA-256 Manifest
Wheel METADATA / sdist PKG-INFO Version Agreement
Hash-only Provenance Generation and Verification
Quick / Standard / Extended Non-mutating Soak Profiles
Independent Machine-readable Soak Report
Environment-aware Threshold Failure Classification
Expanded Alpha Upgrade Fixtures
Expanded External Backup Protection Adapter Contract Tests
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
6. 语义视觉结论必须来自明确且经过认证的 Visual Inspector Result；
7. 生产任务缺少 Tool 时进入可恢复等待状态，不静默回退到 `dry-run`；
8. `dry-run` 只允许测试和开发使用，不得成为生产静默回退；
9. Initial Approval 不自动授权 Revision；
10. Replacement 只有通过最终视觉审查后才能 Supersede Source；
11. Conversation 默认视图不暴露底层 Runtime Identity 或 Private Path；
12. Bearer、Lease、Claim、Signing Key 等 Secret 不写入公共输出；
13. Portable Backup 默认排除 Host Credential Verifier 与 Ledger Signing Key；
14. Restore 默认只生成计划，必须显式 Apply；
15. GUIF 不实现自定义加密算法，不对外部加密工具的强度作虚假保证；
16. External Protection 缺少配置时 Fail Closed，不回退到未保护复制；
17. 未知 Source Release、未来 Schema、无效记录和 Raw Secret Field Fail Closed；
18. Release Provenance 只有真实 Hash Evidence 时才声明 Hash Provenance；
19. 没有真实签名或 Attestation 系统时，不声明签名、可信构建或供应链认证；
20. 性能 Threshold 失败是 Host / Environment Evidence，不能单独描述为产品正确性失败；
21. Breaking Change 必须增加 Public API Version 并提供迁移路径；
22. Legacy `ProviderAdapter` 继续作为显式兼容路径；
23. 公共仓库示例与测试只使用完全虚构的 Fixture；
24. 不得提交用户真实 Theme、Prompt、Image、Conversation Record、Credential、Backup 或 Private Path。

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

Compatibility Contract：

```text
release: 1.0.0-alpha.28
origin_release: 1.0.0-alpha.28
current_release: 1.0.0-beta.2
channel: beta
public_api_version: 1
```

`release` 与 `origin_release` 标识 alpha.28 的冻结起点；`current_release` 标识当前实现版本。

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

### 6. Private Theme、Host Work 与真实图片契约

新 Conversation 在没有 Conversation-level Binding 时必须进入 `theme-confirmation`。允许选择历史 Theme、创建新 Theme、派生不可变新版本或明确不绑定。

真实 Theme Content 存储在：

```text
<private-data-root>/themes/
```

Host Work 支持：

```text
image-generation
image-editing
visual-inspection
```

Host Work 需要 Authenticated Actor、Capability Authorization、Task-scoped Discovery、Task Etag、Exclusive Lease、Actor-bound Claim、Immutable Attachment、Result Contract 与 Idempotent Submission。

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

`ChatGPTHostLoop` 可嵌入 ChatGPT 或其他 Host 环境。Local Python Package 本身不能进入 ChatGPT 产品内部调用 Image Tool。

### 7. Metadata Review、Semantic Review 与 Revision

Metadata Review 只检查可确定的文件与 Contract Evidence，例如：

```text
file exists
regular file
MIME / format
dimensions
alpha channel when required
SHA-256
registered file identity
```

Metadata Review 不得声称以下语义通过：

```text
Theme consistency
composition and hierarchy
content correctness
readability
usability
```

Semantic Result 允许：

```text
passed
review-required
blocked
```

存在可执行 Finding 时：

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

### 8. Pillow Pixel API Compatibility

Protected Region QA 与 Masked Composition 通过统一兼容边界读取 Flattened Pixel Data：

```text
优先：Image.get_flattened_data()
兼容：Image.getdata()
```

旧 API 只在新 API 不存在时显式使用。兼容层不得修改 Pixel Value、Mask Semantics、Tolerance、Protected Pixel Count 或 Feathered Pixel Count。

CI 必须使用：

```bash
pytest -q -W error::DeprecationWarning:PIL
```

任何新的 Pillow Deprecation Warning 都应使 CI 失败，而不是被静默忽略。

### 9. Gated Export

Gated Export 必须保持：

```text
Contract QA passed
Active visual Artifacts semantically passed
Authenticated export capability
Exclusive Task Lease
Engine manifest / transaction evidence
Rollback and Git Change controls
```

GUIF 不得把 Simulation、Metadata-only Result 或缺少语义检查的 Artifact 伪装成可导出的视觉通过结果。

### 10. Portable 与 Full-local Backup

Portable Profile 包含可恢复的用户生产数据，例如：

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

Portable Profile 排除敏感或不可移植的认证材料，例如：

```text
host-credentials
operation-ledger
operation-audit
gateway-requests
```

`full-local` 只有显式 `include_sensitive=True` 或 CLI `--include-sensitive` 时允许创建。未保护 GUIF Archive 只提供完整性，不提供静态加密。

Backup Verification 必须检查 Canonical Member Path、Path Traversal、Duplicate / Unmanifested Member、Symbolic Link、Manifest Hash、Per-file SHA-256 / Size 和 Total Extraction Limit。

Restore 默认：

```text
apply = false
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

GUIF 不实现自定义密码学。外部 Adapter 环境配置：

```text
GUIF_BACKUP_PROTECTOR_ID
GUIF_BACKUP_PROTECT_COMMAND_JSON
GUIF_BACKUP_UNPROTECT_COMMAND_JSON
GUIF_BACKUP_PROTECT_TIMEOUT_SECONDS
```

Command 必须是 JSON argv Array，并包含 `{input}` 与 `{output}`。

执行规则：

```text
subprocess argv
shell = false
bounded timeout
explicit configuration only
no unprotected fallback
non-empty regular output required
symlink output rejected
existing destination / receipt rejected
atomic temporary publication
source and protected size / SHA-256 evidence
unprotect source SHA-256 verification
```

Protection Receipt 不得保存 Command argv、stdout / stderr、Passphrase、Key、Secret Environment Value、Bearer、Lease 或 Claim。

Contract Test 必须覆盖：

```text
timeout
external non-zero exit
empty output
missing output
symlink output
receipt collision
destination collision
tampered receipt
wrong adapter identity
unprotect hash mismatch
```

Receipt 只提供本地完整性 Evidence，不等同于数字签名。外部算法强度、Key Custody、Rotation 和 Disaster Recovery 由外部 Tool / Operator 负责。

### 12. Supported Upgrade Assurance

支持的 Source Release：

```text
1.0.0-alpha.27
1.0.0-alpha.28
```

默认要求至少一个 Portable Backup。Upgrade Plan 检查 Source Support、Backup Presence、Private Schema Scan、Migration Requirement、Blocked Record 和 Public API Preservation。

公共 Fixture Matrix 必须覆盖：

```text
alpha.27 current record
alpha.27 migration-required record
alpha.28 current record
alpha.28 migration-required record
unknown future schema
invalid JSON
secret-like field
backup missing
backup present
```

所有 Fixture 必须完全虚构。Secret-like Field 检查只返回字段路径，不回显 Secret Value。

完整 Migration Evidence 只保存在 Private Upgrade / Migration Report。公共结果不得返回 Private Path。

### 13. Fault Injection

Fault Injection 默认关闭。环境启用必须同时设置：

```text
GUIF_FAULT_POINTS
GUIF_ALLOW_FAULT_INJECTION=1
```

只设置 Fault Point 而没有 Allow Flag 必须报错。生产环境应保持两者未设置。

故障后必须验证：

```text
source preserved
temporary output cleaned
no half-published destination
no unprotected fallback
```

### 14. Extended Non-mutating Soak Profiles

Profile：

```text
quick       10 iterations
standard    100 iterations
extended    1000 iterations
```

`--iterations` 可显式覆盖为 Custom Profile，最大 10000。检查保持非变更型：

```text
Project Validation
Private Schema Scan
Operation Ledger Verification
Conversation Stage Derivation without persistence
Optional Backup Verification
```

Report 必须包含：

```text
profile / iterations
successful / failed iterations
total / mean / p50 / p95 / max
threshold / threshold_passed
failure_classification
product_correctness_failed
performance_threshold_failed
sanitized errors
production_state_mutated = false
machine_readable = true
```

`--report` 可独立写出 Machine-readable JSON。性能 Threshold 失败应分类为 `environment-performance-threshold`，除非同时存在真实 Contract Error；不能仅凭机器性能差异宣称产品故障。

### 15. Release Artifact Hash Provenance

CI 必须构建 Wheel 与 sdist。Provenance Generation 必须要求两者同时存在，并从内部 Metadata 读取：

```text
Wheel: *.dist-info/METADATA
sdist: PKG-INFO
```

两者的 Package Name 与 Version 必须一致，并匹配：

```text
name = game-ui-framework
version = 1.0.0b2
```

Manifest 默认位置：

```text
dist/SHA256SUMS.json
```

Manifest 至少包含：

```text
schema_version
provenance_kind = hash-only
signature_present = false
attestation_present = false
package name / version
git_commit
build_environment
artifacts[filename, artifact_type, size_bytes, sha256, metadata]
generated_at
```

Verification 必须拒绝：

```text
invalid manifest
unsupported schema or provenance kind
fake signature / attestation claim
unsafe artifact filename
missing wheel or sdist
size mismatch
SHA-256 mismatch
Package Metadata mismatch
expected Git Commit mismatch
```

Hash Provenance 不能证明 Publisher Identity、Trusted Builder、Timestamp Authority，不能防止攻击者同时替换 Artifact 与 Manifest。没有真实 Signing / Attestation 系统时不得声称更高等级保证。

### 16. CI、Build 与 Wheel Installation

GitHub Actions 必须在以下版本执行：

```text
Python 3.10
Python 3.11
Python 3.12
```

每个 Matrix Job 必须：

```text
install dev dependencies
run tests with Pillow deprecation warnings as errors
build wheel and sdist
generate hash provenance
verify hash provenance
install generated wheel
assert guif.__version__ == 1.0.0b2
run guif-ready contract smoke test
```

只有全部 CI 通过后才允许 Squash Merge。

### 17. Compatibility、Provider 与 Tool Routing

Public API Version 保持 `1`。Breaking Change 必须增加版本并提供 Migration Path。

默认：

```text
Host = ChatGPT
Image Tool = chatgpt-image
Visual Tool = chatgpt-vision
```

Host 与 Tool 均可替换。Legacy `ProviderAdapter` 继续保留为显式 Compatibility Mode。生产任务不得在 Tool 缺失或失败时静默使用 `dry-run`。

### 18. 私有数据与公共仓库边界

公共仓库允许：

```text
Framework code
Schema
CI
Generic bilingual documentation
Wholly fictional fixtures
```

公共仓库禁止：

```text
Real Theme
Real Prompt
Real Image
Real Conversation Record
Credential / Secret
Backup / Protected Backup
Private Path
Private Runtime Evidence
```

Current-tree Audit 不能证明历史 Commit、Fork、Cache 或外部 Clone 已清除；历史事件必须按照 Privacy Migration Guidance 单独处理。

### 19. beta.2 验收标准

beta.2 只有同时满足以下条件才可正式合并：

1. Package Version 为 `1.0.0b2`；
2. Public API Version 仍为 `1`；
3. Frozen Stage 与 Action 未改变；
4. Pillow 新旧 Pixel API 路径均有测试；
5. Protected Region QA 正确性未降低；
6. CI 中 Pillow Deprecation Warning 为零；
7. Wheel 与 sdist 均成功构建；
8. Hash Provenance 成功生成并校验；
9. Wheel / sdist 内部 Version Metadata 一致；
10. 生成的 Wheel 可安装且 `guif.__version__ == 1.0.0b2`；
11. Quick / Standard / Extended Profile 可用且保持 Non-mutating；
12. Threshold Failure 分类测试通过；
13. Upgrade Fixture Matrix 通过；
14. Backup Protection Adapter Contract Matrix 通过；
15. Python 3.10、3.11、3.12 CI 全绿；
16. README.md、README.zh-CN.md、Release Notes、Security Review、Support Policy 与本规格同步；
17. Changed Files 不包含任何真实用户或私有数据；
18. CI 全绿后使用 Squash Merge。

### 20. 已知限制

1. Local Package 不能直接调用 ChatGPT 产品内部 Image Tool；
2. GUIF 不实现密码学，不能判断外部算法强度或恢复丢失 Key；
3. Hash Provenance 不是数字签名或 Trusted Build Attestation；
4. 本地 Timing 受机器与负载影响，不适合直接跨 Host 比较；
5. File-backed Lease / Claim 不是分布式一致性系统；
6. 内置 WSGI Gateway 不是 Internet-edge Reverse Proxy；
7. 尚未实现 Remote Private-data Sync、Retention Automation 与 Multi-device Conflict Resolution；
8. Current-tree Privacy Audit 不能证明历史传播已撤销。

---

## English Version

### 0. Purpose

This living specification defines GUIF beta.2: the frozen Conversation MVP, real image and semantic-review boundaries, private-data controls, backup protection, upgrade assurance, fault injection, non-mutating soak profiles, release artifact hash provenance, compatibility, acceptance criteria, and known limitations.

Features, tests, CI, bilingual READMEs, package metadata, release notes, security review, support policy, and this specification must remain synchronized.

### 1. Product definition

GUIF is a local-first, natural-language-first, configurable Host/Tool execution framework for end-to-end game UI production.

The default contracts are:

```text
Host                  ChatGPT
Image Generation      chatgpt-image
Image Editing         chatgpt-image
Visual Inspection     chatgpt-vision
```

All are replaceable. GUIF Core coordinates projects, private Themes, conversations, plans, approvals, Host Work, Artifacts, review, Revision, export, backup, migration, recovery, diagnostics, soak checks, and release hash provenance.

### 2. Beta.2 scope

Beta.2 is maintenance and provenance hardening. It does not expand the normal user product flow and does not change Public API Version `1`.

The minimum complete scope is:

```text
Pillow flattened-pixel API compatibility
Pillow deprecation warnings treated as CI errors
Wheel and sdist SHA-256 manifest
Artifact package metadata agreement
Hash-only provenance generation and verification
Quick / standard / extended non-mutating soak profiles
Independent machine-readable soak report
Environment-aware performance-threshold classification
Expanded wholly fictional upgrade fixtures
Expanded backup protection adapter contract tests
```

### 3. Non-negotiable principles

- Real user Themes, prompts, images, Conversation records, credentials, backups, and private paths do not enter the public repository.
- Public fixtures are wholly fictional.
- GUIF never fabricates pixels or semantic visual-review outcomes.
- Metadata-only checks cannot claim semantic quality.
- `dry-run` is test/development-only and never a silent production fallback.
- ChatGPT, `chatgpt-image`, and `chatgpt-vision` are defaults, not mandatory Core dependencies.
- Legacy `ProviderAdapter` remains an explicit compatibility path.
- External protection is fail-closed and implements no custom cryptography.
- Hash provenance is not represented as signing or attestation.
- Performance variance is not automatically represented as product failure.
- Breaking changes require a new Public API Version and an explicit migration path.

### 4. Frozen public contract

```text
release: 1.0.0-alpha.28
origin_release: 1.0.0-alpha.28
current_release: 1.0.0-beta.2
channel: beta
public_api_version: 1
```

Frozen stages:

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

Frozen actions:

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

### 5. Image and semantic review boundary

A real visual Artifact must be non-simulation, use a supported MIME type, stay under the allowed root, match its registered SHA-256, expose verified dimensions/format, and satisfy its Output Contract.

Metadata review may verify file identity, format, dimensions, alpha, and hash. It must not claim Theme consistency, composition, content correctness, readability, or usability. Those require an authenticated semantic visual result.

Revision Approval is independent from initial generation Approval. A replacement may supersede its source only after real image production, valid lineage, deterministic checks, and a passing semantic review.

### 6. Pillow compatibility

Flattened pixel access prefers `Image.get_flattened_data()` and falls back to `Image.getdata()` only when the new API is unavailable. The compatibility boundary must not change pixel values, mask meaning, tolerances, protected-pixel counts, or feathered-pixel counts.

CI promotes Pillow deprecation warnings to errors.

### 7. Backup and external protection

Portable backups exclude credential verifiers and operation-ledger signing keys. Restore is plan-first and explicit. Replacement restore creates a portable pre-restore backup and verifies every materialized SHA-256.

External protection uses an explicit argv array, `shell=False`, required `{input}`/`{output}`, bounded timeout, regular non-empty output, symlink rejection, destination/receipt collision rejection, temporary publication, and source/protected SHA-256 evidence. Recovery verifies the original archive hash before publication.

GUIF does not persist command argv, keys, passphrases, or secret environment values. It does not assess cryptographic strength or key custody.

### 8. Upgrade assurance

Supported sources remain alpha.27 and alpha.28. A portable backup is required by default. Unknown sources, future schemas, invalid JSON, and secret-like fields fail closed.

The wholly fictional fixture matrix covers current and migration-required alpha.27/alpha.28 records, future schema, invalid JSON, secret-like field, backup missing, and backup present. Secret values are never echoed.

Full evidence stays in private upgrade/migration reports. Public results omit private paths.

### 9. Non-mutating soak profiles

```text
quick       10 iterations
standard    100 iterations
extended    1000 iterations
```

A custom iteration override is allowed up to 10000. Checks cover project validation, private schema scan, operation-ledger verification, non-persisting Conversation stage derivation, and optional backup verification.

Reports include timing distributions, sanitized errors, threshold status, failure classification, `machine_readable=true`, and `production_state_mutated=false`. A P95 threshold miss alone is classified as environment performance evidence, not product correctness failure.

### 10. Release artifact hash provenance

Both wheel and sdist are required. GUIF reads wheel `METADATA` and sdist `PKG-INFO`, requiring both to match `game-ui-framework` version `1.0.0b2`.

`dist/SHA256SUMS.json` records package metadata, Git commit, build environment, artifact filename/type/size/SHA-256, and internal metadata.

The manifest explicitly declares:

```text
provenance_kind = hash-only
signature_present = false
attestation_present = false
```

Verification rejects modified artifacts, metadata mismatch, unsafe filenames, missing artifact types, unsupported manifest claims, and commit mismatch. Hash provenance does not prove publisher identity, trusted-builder identity, timestamp authority, or resistance to joint artifact/manifest replacement.

### 11. CI and release gate

Each Python 3.10, 3.11, and 3.12 matrix job must:

```text
install development dependencies
run tests with Pillow deprecation warnings as errors
build wheel and sdist
generate and verify hash provenance
install the generated wheel
verify guif.__version__ == 1.0.0b2
run the guif-ready contract smoke test
```

All checks must be green before squash merge.

### 12. Acceptance criteria

Beta.2 is accepted only when version metadata is synchronized, Public API Version remains `1`, frozen stages/actions remain unchanged, Pillow compatibility tests pass without deprecation warnings, wheel/sdist build and metadata checks pass, hash provenance verifies, generated-wheel installation passes, soak profile and threshold tests pass, upgrade and protection contract matrices pass, all Python matrix jobs are green, bilingual documentation is synchronized, and no real private/user data is present.

### 13. Limitations

GUIF cannot directly invoke internal ChatGPT image tools, does not implement cryptography, does not provide release signing or trusted build attestation, cannot normalize timing across unrelated hosts, does not provide distributed consensus for file-backed claims, is not an internet-edge reverse proxy, does not yet provide remote private-data synchronization, and cannot prove removal of previously published data from history, forks, caches, or external clones.
