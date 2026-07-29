# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.25`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF 的产品定位、alpha.25 已验证能力、安全与隐私边界、失败策略、兼容性和下一阶段。Feature、Test、CI、中英文 README、Version Metadata 与本规格必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、以自然语言为主要入口、Host 与 Tool 均可配置、面向游戏 UI 全生产流程的可执行 AI 工作框架。

默认生产路径：

```text
用户与私有 Theme
  -> Planner / Director / Resource / Prompt
  -> Approval Gate
  -> Tool Discovery / Handoff
  -> Authenticated Host Actor
  -> Task Etag + Exclusive Lease
  -> Production Host Gateway
  -> Image Generation / Editing Result Callback
  -> Artifact Registry
  -> Visual Review / Revision
  -> Gated Export
  -> Git Change Set / Commit / Revert
  -> Signed Private Operation Ledger
```

核心原则：

1. Theme、Credential、Task Evidence、Gateway Receipt 与 Ledger 默认属于私有数据；
2. ChatGPT 是默认 Host，但 Host 与 Tool 均可替换；
3. 图片生成与修图由 Host 侧 GPT 或配置的 Tool 执行，GUIF 负责治理、状态和证据；
4. Authentication 与 Authorization 分离；
5. 关键写操作必须校验 Task Etag；
6. 独占写操作必须使用绑定 Actor、Credential 与 Task State 的 Expiring Lease；
7. Gateway POST 必须使用 Idempotency-Key；
8. 一次性 Secret 不得进入 Gateway Receipt 或 Ledger；
9. Callback 必须绑定已有 Handoff、Host、Tool、Execution、Content Hash 与 Task State；
10. Operation Ledger 必须能发现内容修改、链断裂和尾部删除；
11. Git 写入必须先 Plan 与 Diff，再创建独立 Branch 和 Commit；
12. 用户真实 Theme 不得进入公开框架 Git。

### 2. alpha.25 已验证能力

#### 2.1 Production Host Gateway

新增 WSGI Entry Point：

```text
guif-gateway
```

默认：

```text
host = 127.0.0.1
port = 8765
max body = 32 MiB
CORS = disabled
Cache-Control = no-store
```

非 Loopback Bind 必须同时满足：

```text
--allow-remote
--tls-cert
--tls-key
TLS >= 1.2
```

缺少任一条件时拒绝启动。

已实现 Endpoint：

```text
GET  /health
GET  /v1/descriptor
GET  /v1/tasks/{project}/{task_id}/summary
POST /v1/tasks/{project}/{task_id}/lease
POST /v1/tasks/{project}/{task_id}/approvals/{approval_id}
POST /v1/tasks/{project}/{task_id}/callbacks/{handoff_id}
POST /v1/tasks/{project}/{task_id}/exports
GET  /v1/ledger/verify
GET  /v1/ledger/entries?limit=100
```

`/health` 不要求认证；其他 `/v1` Endpoint 必须使用 GUIF Bearer Credential。

#### 2.2 Capability Authorization

Gateway Capability：

```text
gateway:read
task:read
ledger:read
task:lease
approval:decide
tool-result:submit
export:execute
```

Credential 有效但缺少对应 Capability 时，操作被拒绝。

#### 2.3 Request Boundary

Gateway 对请求执行：

```text
Content-Length validation
maximum body size
UTF-8 JSON object validation
safe path segment validation
Task Etag format validation
required header validation
raw callback body handling
```

Error Mapping：

```text
AuthenticationError -> 401
Invalid Request -> 400
Not Found -> 404
Concurrency / Lease / Idempotency Conflict -> 409
Oversized Body -> 413
Rejected Callback / Export -> 422
Invalid Ledger -> 503
Unexpected Error -> 500 without internal traceback disclosure
```

#### 2.4 Idempotency

每个 POST 必须提供：

```text
Idempotency-Key: 1-128 visible ASCII characters
```

Private Receipt：

```text
<private-data-root>/gateway-requests/request-<hash>.json
```

Receipt 保存：

```text
request id
idempotency key hash
method + path
request fingerprint
status
HTTP status
sanitized response or error
created / completed time
```

不保存：

```text
Bearer Token
Lease Token
Raw Image Bytes
Credential Verifier
```

Lease Token 是一次性 Secret。同一个 Lease Request 的重复调用不会再次返回 Token。Callback、Approval 与 Export 的安全重复调用返回已保存的非敏感 Receipt，不重复执行写入。

#### 2.5 Raw Image Callback

Callback Body 直接使用图片 Bytes，不要求 Base64：

```text
Authorization: Bearer ...
Idempotency-Key: ...
If-Match or X-GUIF-Task-Etag
X-GUIF-Lease-Token
X-GUIF-Filename
Content-Type
optional X-GUIF-Content-SHA256
optional width / height / model / tool / request id
```

校验：

1. Bearer Credential；
2. `tool-result:submit` Capability；
3. Persisted Handoff；
4. Host 与 Tool Identity；
5. Active Lease Ownership；
6. Task Etag；
7. Body Size；
8. Content SHA-256；
9. Handoff Status；
10. Deterministic Callback Identity；
11. Artifact Registration；
12. Lease Consumption。

#### 2.6 Signed Operation Ledger

Private Layout：

```text
<private-data-root>/operation-ledger/
  signing-key.json
  entries.jsonl
  head.json
```

算法：

```text
HMAC-SHA256 chain v1
random 256-bit private key
canonical JSON
payload SHA-256
entry SHA-256
previous entry hash
signed head checkpoint
```

Entry：

```text
schema_version
sequence
entry_id
operation_id
occurred_at
operation
status
actor
scope
details
previous_entry_hash
key_id
payload_hash
entry_hash
signature
```

Authenticated Runtime Operation 写入：

```text
started
completed or failed
```

Gateway Request 写入：

```text
gateway.request completed or failed
```

验证可以发现：

```text
invalid JSON entry
sequence mismatch
previous hash mismatch
payload modification
entry hash modification
signature mismatch
key identity mismatch
missing head
head mismatch
missing tail entry
```

Ledger 不保存 Bearer Token、Lease Token、Raw Image Bytes 或 Credential Secret。

#### 2.7 Ledger Inspection

CLI：

```text
guif-ledger descriptor
guif-ledger verify
guif-ledger list
```

Runtime API：

```python
runtime.operation_ledger_descriptor()
runtime.verify_operation_ledger()
runtime.list_operation_ledger(limit=100)
```

Ledger Verification 失败时，新的 Authenticated Runtime Mutation Fail Closed。

#### 2.8 Authenticated Runtime Coverage

alpha.25 Ledger-backed Operation：

```text
host.credential.register
host.credential.revoke
host.credential.rotate
task.lease.acquire
task.lease.renew
task.lease.release
host.callback.submit
approval.decide
export.execute
export.rollback
git.change.prepare
git.change.commit
git.change.revert
```

#### 2.9 Existing Governance

alpha.25 继续保留并验证：

```text
Private Theme Library
Conversation Theme Resolution
Prompt IR
Approval Gate
Tool Discovery and Connection
ChatGPT Host Handoff
Artifact Registry
Metadata Visual Review
Controlled Revision
Gated Export
Rollback
Git Change Set
Privacy Audit
```

### 3. 私有数据边界

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  project-theme-bindings/
  host-credentials/
  gateway-requests/
  operation-ledger/
  runs/<project>/<task-id>/
  plans/
  migrations/
  privacy-reports/
```

公开 Framework Git 允许：

```text
Code
Schema
Generic Contract
Fictional Fixture
Generic Documentation
```

公开 Framework Git 禁止：

```text
真实用户 Theme
真实视觉规则与对话迭代
Bearer / Lease Secret
Credential Verifier
Private Runtime Evidence
Raw User Artifact
```

### 4. 安全边界

#### 4.1 已保证

- Local Bearer Authentication；
- Capability Authorization；
- Constant-time Credential Verification；
- Task Optimistic Concurrency；
- Exclusive Expiring Lease；
- Callback Identity and Hash Validation；
- POST Idempotency；
- Loopback Default；
- Remote TLS Requirement；
- Request Body Limit；
- Private Receipt；
- Local HMAC Chain Tamper Evidence；
- No Secret Persistence in Gateway Receipt or Ledger。

#### 4.2 未保证

- OIDC；
- mTLS Client Identity；
- Hardware-backed Key；
- Distributed Lock；
- Cross-process Ledger Lock；
- Public-key Non-repudiation；
- External Timestamp Authority；
- Remote Immutable Audit Log；
- Internet-edge DDoS Protection；
- Automated Certificate Rotation；
- Encryption at Rest；
- Automatic ChatGPT Product Integration；
- Remote Git Push / PR / Protected Branch Negotiation。

### 5. 失败策略

```text
Missing Credential -> reject
Missing Capability -> reject
Stale Etag -> reject
Invalid or Expired Lease -> reject
Missing Idempotency-Key -> reject
Reused Key with different request -> reject
One-time Secret replay -> reject
Oversized Body -> reject
Invalid Callback Identity -> reject
Invalid Ledger -> reject new authenticated mutation
Remote bind without TLS -> refuse startup
```

不允许静默回退到 `dry-run`。

### 6. 兼容性

旧版未认证 Runtime API 继续存在，以避免 Alpha 期间破坏已有调用方；它们不具备 alpha.25 的 Gateway、Lease 与 Ledger Guarantee。新生产集成应使用 Gateway 或 Authenticated Runtime API。

### 7. alpha.25 Release Acceptance

- Gateway 可启动；
- Loopback Health Endpoint 可用；
- Remote Bind 无 TLS 时拒绝；
- Bearer + Capability 生效；
- Lease Endpoint 返回一次性 Token；
- Lease Replay 不泄露 Token；
- Raw Image Callback 登记一个 Artifact；
- Callback Replay 不创建重复 Artifact；
- Body Limit 生效；
- Ledger 能验证正常 Chain；
- Ledger 能发现内容篡改；
- Ledger 能发现尾部删除；
- Python 3.10 / 3.11 / 3.12 CI 通过；
- README、中文 README、Version 与本规格一致。

### 8. 下一阶段

**alpha.26：Real ChatGPT Image Loop + Default Visual Inspector**

目标：

```text
Host 自动读取 Handoff
-> ChatGPT/GPT 执行 Image Generation or Editing
-> Gateway 自动回传
-> Default Semantic Visual Inspector
-> Revision Plan
-> User Approval
-> Automatic Editing Retry
-> Review-gated Supersession
-> Gated Export
```

必须增加真实 End-to-end Acceptance Test，并停止扩大非核心架构范围。

---

## English Version

### 0. Purpose

This living specification defines GUIF's product position, verified alpha.25 behavior, security and privacy boundaries, failure policy, compatibility, and next milestone. Features, tests, CI, both READMEs, version metadata, and this specification must remain synchronized.

### 1. Product Definition

GUIF is a local-first executable AI work framework for end-to-end game UI production. Natural language is the primary entry point. Hosts and Tools are configurable; ChatGPT and `chatgpt-image` are defaults, not Core dependencies.

```text
private user Theme
  -> planning / contracts / Approval
  -> Tool handoff
  -> authenticated Host actor
  -> Task etag + exclusive lease
  -> Production Host Gateway
  -> image generation/editing callback
  -> Artifact / review / revision
  -> Gated Export
  -> Git change / commit / revert
  -> signed private Operation Ledger
```

### 2. Verified alpha.25 Behavior

The release provides:

- a runnable loopback-first WSGI Host Gateway;
- explicit TLS requirements for non-loopback binding;
- bearer authentication and capability authorization;
- Task summary, lease, Approval, callback, Export, and ledger endpoints;
- raw binary image callbacks;
- request body limits and structured error mapping;
- required POST idempotency keys;
- private idempotency receipts without bearer, lease, or image secrets;
- one-time lease secret semantics;
- callback replay without duplicate Artifact creation;
- a private HMAC-SHA256 append-only chain;
- a signed head checkpoint that detects tail deletion;
- ledger-backed authenticated Runtime operations;
- `guif-gateway` and `guif-ledger` commands.

### 3. Operation Ledger Boundary

The ledger is local tamper evidence. It is not a public-key signature, third-party timestamp, remote immutable log, or defense against an attacker who possesses the private HMAC key and can rewrite the full private store.

### 4. Privacy Boundary

Real Themes, conversations, credentials, Gateway receipts, ledger keys and entries, Task Runs, callback evidence, and user Artifacts remain outside framework Git by default. The public repository contains only implementation, contracts, generic documentation, and fictional fixtures.

### 5. Fail-closed Policy

Authenticated mutations are rejected for missing capability, stale Task state, invalid lease, invalid callback identity, missing idempotency, request replay conflicts, oversized content, invalid ledger integrity, or unsafe remote binding.

### 6. Compatibility

Legacy unauthenticated Runtime methods remain during the Alpha period, but they do not carry alpha.25 Gateway, lease, or ledger guarantees. New production integration must use the Gateway or authenticated Runtime APIs.

### 7. Next Milestone

**alpha.26: Real ChatGPT Image Loop + Default Visual Inspector** will automate Host-side handoff consumption, GPT image generation/editing, Gateway submission, default semantic visual inspection, approval-driven revision retry, and an end-to-end runnable project acceptance test.
