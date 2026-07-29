# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.24`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF 的产品定位、已验证能力、安全与隐私边界、失败策略、兼容性和下一阶段。Feature、Test、CI、中英文 README、Version Metadata 与本规格必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、以自然语言为主要入口、Host 与 Tool 均可配置、面向游戏 UI 全生产流程的可执行 AI 工作框架。

alpha.24 的默认生产路径：

```text
用户与私有 Theme
  -> Planner / Director / Theme / Resource / Prompt
  -> Approval Gate
  -> Tool Discovery / Handoff
  -> Authenticated Host Actor
  -> Task Etag + Exclusive Lease
  -> Authenticated Callback
  -> Artifact Registry
  -> Visual Review / Revision
  -> Gated Export
  -> Git Change Set Plan / Diff
  -> Dedicated Branch / Commit
  -> Optional Revert Commit
```

核心原则：

1. Theme、Credential、Task Evidence 与 Callback Evidence 默认属于私有数据；
2. Host 写操作必须能关联到明确、可验证的 Actor；
3. Authentication 与 Authorization 分离：有效 Credential 不代表拥有所有 Capability；
4. 所有关键写操作必须检查当前 Task Etag；
5. 独占操作必须使用有过期时间、绑定 Actor 的 Task Lease；
6. Callback 必须绑定已存在的 Handoff、Tool、Execution、Content Hash 与 Host Identity；
7. Git 写入必须先 Plan 和 Diff，再创建独立 Branch 与 Commit；
8. Git HEAD 或 Task State 发生变化时 Fail Closed；
9. Revert 必须生成正常 Git Commit，不直接隐藏或覆盖历史；
10. 旧版字符串 Actor API 暂时保留兼容性，但不声明具备 alpha.24 认证保证。

### 2. alpha.24 已验证能力

#### 2.1 Private Host Credential Store

`HostCredentialStore` 将 Credential 保存到 Private Data Root：

```text
<private-data-root>/host-credentials/<credential-id>.json
```

Registration 输入：

```text
actor_id
host_id
capabilities
roles
created_by
optional expires_at
```

Registration 输出：

```text
credential metadata
one-time bearer token
secret_visible_once = true
```

Bearer Token 格式：

```text
guifh1.<credential-id>.<secret>
```

持久化 Record 不保存原始 Secret，只保存：

```text
PBKDF2-HMAC-SHA256 verifier
random salt
iteration count
status and lifecycle metadata
```

支持：

```text
register
list
get
revoke
rotate
authenticate
```

`authenticate()` 使用 Constant-time Compare，并检查：

- Token Format；
- Credential 是否存在；
- Schema；
- Active / Revoked Status；
- Expiration；
- Expected Host Identity；
- Secret Verifier；
- Required Capability。

#### 2.2 Authenticated Actor Contract

成功认证后生成：

```json
{
  "schema_version": 1,
  "actor_id": "production-host",
  "host_id": "chatgpt",
  "credential_id": "cred-...",
  "capabilities": ["task:lease", "tool-result:submit"],
  "roles": ["operator"],
  "issuer": "guif-local",
  "authentication_method": "private-bearer-token",
  "authenticated_at": "...",
  "authenticated": true
}
```

Actor Snapshot 会进入 Approval、Callback、Export 和 Git Change Evidence。

#### 2.3 Task Etag

`task_etag()` 对持久化安全的 `Task.to_dict()` 进行 Canonical JSON SHA-256：

```text
task-sha256:<digest>
```

Etag 覆盖 Task Status、Context Reference、State、Output、Event、Error 与时间字段。完整私有 Theme Content 已在 `RuntimeContext.to_dict()` 中 Redact，因此不会因 Etag 计算而进入 Task 文件。

所有 alpha.24 写操作都接收 `expected_task_etag`。不匹配时抛出 `ConcurrencyError`，不执行写入。

#### 2.4 Exclusive Task Lease

Lease Record：

```text
<private-data-root>/runs/<project>/<task-id>/task-lease.json
```

Lease Token：

```text
guifl1.<lease-id>.<secret>
```

Lease 绑定：

```text
project
task_id
lease_id
purpose
authenticated actor
base_task_etag
token hash
acquired_at
expires_at
ttl_seconds
status
```

状态：

```text
active
expired
released
consumed
```

限制：

- TTL 最短 15 秒、最长 3600 秒；
- 同一 Task 同时只能存在一个 Active Lease；
- Lease Token 只显示一次；
- Token Hash、Actor、Credential、Task Etag 和 Expiration 必须全部匹配；
- 成功写操作消费 Lease；
- 读取操作不需要 Lease；
- Lease 可显式 Renew 或 Release。

#### 2.5 Stable Authenticated Host Callback

`submit_authenticated_tool_result()` 是 alpha.24 的生产 Host Result Contract。

输入：

```text
project
task_id
handoff_id
bearer_token
lease_token
expected_task_etag
content
filename
mime_type
optional content_sha256
optional dimensions / model / tool / request_id / metadata
```

校验顺序：

1. 读取 Persisted Handoff；
2. 根据 Handoff Host ID 认证 Credential；
3. 检查 `tool-result:submit` Capability；
4. 校验 Content SHA-256；
5. 校验 Tool ID、Execution ID 与 Handoff Status；
6. 计算 Deterministic Callback ID；
7. 检查 Idempotency；
8. 校验 Lease 与 Task Etag；
9. 调用既有 Tool Result Registration；
10. Persist Callback Evidence；
11. Consume Lease。

Callback Record：

```text
host-callbacks.json
```

包含：

```text
callback_id
status
authenticated actor
lease snapshot
envelope
content_sha256
execution / handoff / tool identity
artifact_id
completed_at
```

Callback ID 由 Project、Task、Handoff、Execution、Tool、Request、Credential、Content Hash、Filename 与 MIME 共同确定。

#### 2.6 Authenticated Approval

`decide_approval_authenticated()` 要求：

```text
approval:decide
task:lease
matching task etag
active lease
```

支持：

```text
approved
rejected
changes-requested
```

Approval Record 与 History 会附加：

```text
authenticated_actor
lease_id
```

旧版 `approve()`、`reject()` 与 `request_changes()` 继续存在，但只保留兼容性。

#### 2.7 Authenticated Gated Export

`execute_gated_export_authenticated()` 要求：

```text
export:execute
task:lease
matching task etag
active lease
existing Gated Export rules
```

完成后，Export Record 与 Transaction 会关联 Authenticated Actor 与 Lease ID。

`rollback_gated_export_authenticated()` 要求 `export:rollback`，并继续执行既有 Hash Conflict Check、Backup Check 与 Force Reason Audit。

#### 2.8 Git Change Set Plan

`prepare_export_git_change()` 只接受 Completed Gated Export。

Plan 阶段：

- 校验 `git:prepare` Capability；
- 校验 Task Etag；
- 解析本地 Git Repository Root；
- 确认 Project 位于 Repository 内；
- 加载 Export Transaction；
- 收集 Transaction Mutation Path；
- 收集 Engine Output Files；
- 纳入 Transaction Record；
- 记录 Base HEAD 与 Current Branch；
- 校验 Proposed Branch Name；
- 记录 Selected Path 的 Working Tree Status；
- Persist `git-changes.json`；
- 不修改 Git Branch、Index 或 Commit。

Git Change Set Record 包含：

```text
change_set_id
task_id
project
export_id
status
actor
repository_root
project_root
base_head
base_branch
branch
message
paths
working_tree_status
transaction path and sha256
prepared_from_task_etag
commit
revert
error
```

状态：

```text
ready
no-changes
failed
committed
reverted
```

#### 2.9 Git Diff

`diff_git_change()` 返回：

```text
tracked working-tree diff
untracked file no-index diff
working-tree status
diff SHA-256
selected paths
base HEAD
```

Diff 为 Read-only 操作，不创建 Branch、不修改 Index。

#### 2.10 Git Commit

`execute_git_change()` 要求：

```text
git:commit
task:lease
matching task etag
active lease
Change Set status = ready
current Git HEAD = planned base_head
proposed branch does not exist
current branch has a name
```

执行步骤：

1. 创建 Dedicated Branch；
2. Stage 仅 Selected Paths；
3. 确认 Selected Staged Set 非空；
4. 计算 Staged Diff SHA-256；
5. Commit 仅 Selected Paths；
6. Persist Commit SHA、Parent、Branch、Message、Paths 与时间；
7. 将 Commit 关联回 Gated Export；
8. Consume Lease。

若执行失败，GUIF 尝试 Unstage、切回 Original Branch 并删除未成功提交的 Branch，同时保存 Failed Record。Project Working Tree 内容不会被静默删除。

#### 2.11 Git Revert

`revert_git_change()` 要求：

```text
git:revert
task:lease
matching task etag
active lease
Change Set status = committed
selected paths clean
```

执行正常 `git revert --no-edit <commit>`，保存 Revert Commit、Actor、Reason 与时间，并关联回 Export。

若 Selected Paths 有新的 Uncommitted Change，操作 Fail Closed。

#### 2.12 Operational CLI

新增独立 Entry Point：

```text
guif-ops
```

Bearer Token 默认从：

```text
GUIF_HOST_TOKEN
```

Lease Token 默认从：

```text
GUIF_TASK_LEASE
```

因此 Secret 不需要作为普通命令参数进入 Shell History。

命令组：

```text
credential-create / list / revoke / rotate
task-etag
lease-show / acquire / renew / release
callback-submit / list / show
approval-decide
export-execute / export-rollback
git-plan / list / show / diff / commit / revert
summary
```

#### 2.13 Private Runtime Evidence

Task Run Directory 新增：

```text
task-lease.json
host-callbacks.json
git-changes.json
```

`run-list` 新增：

```text
authenticated_callback_count
task_lease_status
git_change_count
committed_git_change_count
latest_git_change_status
```

### 3. Security Boundary

#### 3.1 认证保证覆盖

alpha.24 保证：

- Bearer Secret 不以明文持久化；
- Credential 可吊销和轮换；
- Capability 不足时拒绝操作；
- Host Callback 与 Handoff Host Identity 一致；
- Task Etag 阻止 Stale Write；
- Lease 阻止遵循新协议的并发写操作；
- Callback Content 可通过 SHA-256 验证；
- Git Commit 与 Revert 具有明确 Actor、Task、Export 与 Diff Provenance。

#### 3.2 不在保证范围

alpha.24 不保证：

- OIDC、mTLS 或 Hardware-backed Key；
- OS-level、Database 或 Distributed Lock；
- Legacy API 自动遵守 Lease；
- Network Callback Authentication；
- Remote Git Server 身份与权限；
- Protected Branch Policy；
- Signed Manifest 或 Non-repudiation；
- Private File Encryption-at-rest。

### 4. Privacy Boundary

以下内容必须位于 Private Data Store：

- Host Credential Verifier；
- Lease Token Hash 与 Actor Snapshot；
- Callback Envelope 与 Result Evidence；
- Task、Prompt、Review、Revision 与 Approval Evidence；
- 完整 Theme Content；
- 自然语言 Plan。

Project Git 只应接收用户明确批准的 Project Truth、Engine Output 与相关 Transaction Record。

### 5. Compatibility and Migration

- Task Schema 未因 alpha.24 强制升级；Etag 从现有安全序列化结果计算；
- 旧 Task Run 仍可加载；
- `submit_tool_result()`、字符串 Actor Approval 与字符串 Actor Export API 继续存在；
- 新生产集成应迁移到 Authenticated API；
- Existing Gated Export 可在完成后生成 Git Change Set；
- Existing Project 不需要自动创建 Git Repository；缺少 Git 时显式报错；
- Existing Remote 不会被自动修改或 Push。

### 6. Failure Strategy

统一 Fail-closed 条件：

```text
invalid or revoked credential
missing capability
wrong host identity
stale task etag
missing / expired / wrong-owner lease
content hash mismatch
handoff not waiting
Git repository missing
Git HEAD changed
branch already exists
selected paths have revert conflicts
no staged selected changes
```

失败必须：

- 不伪造成功状态；
- 保存 Error Type 与 Message；
- 保留 Task、Artifact、Export 与 Git Provenance；
- 不自动改用 Legacy API；
- 不自动 Push Remote；
- 不自动 Force Revert。

### 7. 当前边界

- Host Credential Store 为本地文件系统；
- Bearer Token Rotation 不会自动通知外部 Host；
- Lease 不是跨进程强锁；
- Callback 仍由本地 API / CLI 接收；
- Git Change Service 依赖本地 Git 与已配置 Author；
- Git Branch 与 Commit 只在本地创建；
- Remote Push、PR、Server Check 与 Protected Branch Integration 尚未实现；
- Signed Callback / Export / Git Receipt 尚未实现；
- Crash Recovery 目前依赖 Persisted Record，尚无 Operation Journal Replay；
- 默认 Semantic Visual Inspector Registry 为空；
- Current-tree Privacy Audit 无法证明历史或外部副本已清理。

### 8. 下一阶段

#### alpha.25：Production Host Gateway 与 Signed Operation Ledger

目标：

- Network Callback Transport；
- OIDC 或 Pluggable Identity Provider；
- Cross-process Lock 与 Lease Fencing Token；
- Signed Callback Receipt；
- Signed Export / Git Manifest；
- Durable Operation Journal 与 Crash Recovery；
- Remote Git Push 与 PR Creation；
- Protected Branch、Required Check 与 Merge Policy；
- Remote Failure Retry、Pause、Cancel 与 Timeout Summary。

### 9. 迭代记录

- `alpha.16`：Persistent Approval；
- `alpha.17`：Provider Adapter 与 Artifact Registry；
- `alpha.18`：Visual Review 与 Revision Plan；
- `alpha.19`：Configurable Host / Tool 与 ChatGPT Handoff；
- `alpha.20`：Controlled Revision Execution；
- `alpha.21`：Tool Discovery 与 Connection Workflow；
- `alpha.22`：Gated Export 与 Transaction Rollback；
- `alpha.23`：Private Theme Library、Conversation Theme Resolution 与 Privacy Boundary；
- `alpha.24`：Authenticated Actor、Task Etag、Lease、Host Callback 与 Git Change Set。

---

## English Version

### 0. Purpose

This file defines GUIF's product direction, verified capabilities, security and privacy boundaries, failure behavior, compatibility, and next phase. Features, tests, CI, both READMEs, version metadata, and this specification must agree in the same release.

### 1. Product definition

GUIF is a local-first executable AI work framework for end-to-end game UI production. Hosts and Tools are configurable; ChatGPT remains the default Host.

Alpha.24 adds an authenticated operational boundary around persisted Task writes and Project Git changes.

### 2. Verified alpha.24 capabilities

- private file-backed Host credentials with one-time bearer secrets;
- PBKDF2-HMAC-SHA256 secret verifiers, revocation, rotation, and expiration;
- normalized authenticated actor snapshots with roles and capabilities;
- deterministic Task etags over privacy-safe Task serialization;
- exclusive expiring Task leases bound to actor, credential, purpose, and base etag;
- stable authenticated external Tool result callbacks;
- callback Host, Tool, Execution, Handoff, lease, etag, and content-hash validation;
- idempotent Callback identity and persisted callback evidence;
- authenticated Approval and Gated Export wrappers;
- Task-bound Git Change Set planning from completed Gated Exports;
- read-only tracked and untracked diff generation;
- base-HEAD guarded dedicated-branch commit execution;
- Export-to-Commit linkage and staged-diff SHA-256;
- normal Git revert commits with selected-path conflict checks;
- private persisted `task-lease.json`, `host-callbacks.json`, and `git-changes.json`;
- separate `guif-ops` CLI using secret environment variables.

### 3. Security boundary

Alpha.24 verifies local bearer credentials, explicit capabilities, Host identity, Task etags, logical exclusive leases, callback content hashes, and Git base HEAD. It does not yet provide OIDC, mTLS, hardware-backed keys, distributed locks, a network callback server, remote Git authorization, protected-branch negotiation, or cryptographically signed receipts.

Legacy unauthenticated APIs remain available for compatibility and can bypass the new logical lease boundary. Production integrations should use authenticated methods.

### 4. Git boundary

Git Change Set preparation is non-mutating. It records the repository root, Project root, completed Export, transaction hash, base HEAD, selected paths, proposed branch, commit message, and working-tree status.

Execution requires a fresh Task lease and unchanged base HEAD. GUIF creates a dedicated local branch, stages only selected paths, commits them, and links the commit to the Export. It does not push a remote or create a pull request.

Revert creates a normal Git revert commit and fails closed if selected paths contain newer uncommitted changes.

### 5. Privacy boundary

Credential verifiers, leases, callback evidence, Task Runtime evidence, natural-language Plans, and complete Theme content remain in private storage. Project Git receives only explicitly approved Project truth, Engine output, and selected transaction evidence.

### 6. Compatibility

Task schema compatibility is preserved. Existing Runs and legacy Actor APIs remain readable and callable. Missing Git repositories or Git author configuration produce explicit failures. GUIF never creates or pushes a remote automatically.

### 7. Current limitations

The credential and lease stores are local files. Leases are not OS or distributed locks. Callback transport is local API/CLI only. Git operations are local. Signed manifests, remote push/PR integration, protected-branch checks, operation-journal replay, encryption-at-rest, and authenticated remote identities are not implemented.

### 8. Next phase

**alpha.25: Production Host Gateway and Signed Operation Ledger** will add network callback transport, OIDC or pluggable identity verification, cross-process lock fencing, signed Callback/Export/Git receipts, durable recovery, remote Git push and pull-request integration, protected-branch checks, and remote operation lifecycle controls.
