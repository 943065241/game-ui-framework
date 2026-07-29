# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，但二者都不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-alpha.25` 新增可运行的 Authenticated Production Host Gateway，以及私有 Signed Operation Ledger。

```text
选择私有 Theme
  -> Prompt / Approval / Tool Handoff
  -> Authenticated Host Actor
  -> Task Etag + Exclusive Lease
  -> Production Host Gateway
  -> Image Result Callback
  -> Artifact / Review / Revision
  -> Gated Export
  -> Git Change Set / Commit / Revert
  -> Signed Private Operation Ledger
```

中英文双语产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。隐私迁移和 Git 历史处理指引见 [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md)。

## Production Host Gateway

启动本地 Gateway：

```bash
pip install -e .[dev]
guif-gateway --workspace . --host 127.0.0.1 --port 8765
```

默认只绑定 Loopback。绑定非本机地址时，必须同时显式启用 `--allow-remote` 并提供 TLS 证书和私钥：

```bash
guif-gateway \
  --host 0.0.0.0 \
  --port 8765 \
  --allow-remote \
  --tls-cert server.crt \
  --tls-key server.key
```

内置服务是一个受控单机 Host Boundary，不是面向公网的边缘反向代理。真实部署仍应在外层配置符合项目策略的网络隔离、证书轮换、限流和进程托管。

### Gateway Endpoint

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

所有 `/v1` Endpoint 都要求带有相应 Capability 的 GUIF Bearer Credential。所有 POST 写操作都要求 `Idempotency-Key`；独占写操作还要求 Task Etag 与 Lease Token。

### 创建 Gateway Credential

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
issued = runtime.register_host_credential(
    actor_id="production-host",
    host_id="chatgpt",
    capabilities=(
        "gateway:read",
        "task:read",
        "ledger:read",
        "task:lease",
        "approval:decide",
        "tool-result:submit",
        "export:execute",
        "export:rollback",
        "git:prepare",
        "git:commit",
        "git:revert",
    ),
    roles=("operator",),
    created_by="local-admin",
)

bearer_token = issued["bearer_token"]  # 只显示一次
```

GUIF 只保存 PBKDF2-HMAC-SHA256 Verifier，不保存原始 Bearer Secret。

### 通过 HTTP 获取 Task Lease

```http
POST /v1/tasks/SampleGame/task-123/lease
Authorization: Bearer guifh1....
Content-Type: application/json
Idempotency-Key: lease-2026-001

{
  "expected_task_etag": "task-sha256:...",
  "ttl_seconds": 300,
  "purpose": "host-result-callback"
}
```

Lease Token 只返回一次，不会写入 Gateway Idempotency Receipt。重复同一个 Lease Request 不能再次取得 Token。

### 提交生成或修图结果

Callback Body 直接传输图片文件，避免 Base64 膨胀：

```http
POST /v1/tasks/SampleGame/task-123/callbacks/handoff-456
Authorization: Bearer guifh1....
Idempotency-Key: result-2026-001
If-Match: "task-sha256:..."
X-GUIF-Lease-Token: guifl1....
X-GUIF-Filename: generated-screen.png
X-GUIF-Content-SHA256: <sha256>
X-GUIF-Width: 1080
X-GUIF-Height: 2340
X-GUIF-Model-ID: image-model
Content-Type: image/png

<原始 PNG Bytes>
```

Gateway 会检查 Credential Capability、Host/Tool/Handoff Identity、Task Etag、Lease Ownership、Body Size、可选 Content SHA-256 和 Idempotency，然后才登记 Artifact。成功 Callback 的重复提交只返回已保存的非敏感 Receipt，不会创建重复 Artifact。

默认 Body 上限为 32 MiB，可通过 `--max-body-mb` 调整。

## Signed Operation Ledger

Authenticated Runtime 操作与 Gateway Request 结果会追加到私有 HMAC-SHA256 Chain：

```text
<private-data-root>/operation-ledger/
  signing-key.json
  entries.jsonl
  head.json
```

每条 Entry 记录：

```text
Sequence
Operation + Status
Authenticated Actor Snapshot
Project / Task / Object Scope
脱敏后的 Request 与 Result Evidence
Previous Entry Hash
Payload Hash
Entry Hash
HMAC Signature
```

Signed Head Checkpoint 可以发现 Entry 被修改、顺序断裂、中间 Entry 缺失和尾部 Entry 被删除。

检查命令：

```bash
guif-ledger --workspace . descriptor
guif-ledger --workspace . verify
guif-ledger --workspace . list --limit 50
guif-ledger --workspace . list --operation host.callback.submit
```

Runtime API：

```python
report = runtime.verify_operation_ledger()
entries = runtime.list_operation_ledger(limit=100)
```

该 Ledger 提供的是**本地篡改证据**，不是 Public-key Non-repudiation。能够取得私有 Ledger Key 并重写全部私有文件的攻击者，仍可伪造一条替代 Chain。alpha.25 不提供外部时间戳机构或远程不可变日志。

## Authenticated Operation

每个持久化 Task 都有确定性 Etag：

```python
etag = runtime.get_task_etag("SampleGame", task_id)
```

独占写操作使用带过期时间的 Task Lease，并绑定 Project、Task、Actor、Credential、Purpose 与 Base Etag。Stale State、Expired Lease、错误 Actor、错误 Credential 和篡改 Token 都会 Fail Closed。

经过认证的 API 包括：

```text
acquire_task_lease / renew_task_lease / release_task_lease
submit_authenticated_tool_result
decide_approval_authenticated
execute_gated_export_authenticated
rollback_gated_export_authenticated
prepare_export_git_change
execute_git_change
revert_git_change
```

每个直接调用的 Authenticated Runtime Operation 都会写入 `started`，以及 `completed` 或 `failed` Ledger Entry。Bearer Token、Lease Token、图片 Bytes 和 Credential Verifier 不会进入 Ledger Detail。

## 私有 Theme Boundary

真实用户 Theme 仍是用户拥有、可版本化的私有数据，不进入框架 Git 或 Project Git：

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

新的视觉设计对话必须选择历史 Theme、新建 Theme、派生新版本，或明确选择暂不绑定。持久化 Task Context 只保存 Theme ID、Version、Snapshot Hash 与 Privacy Marker；完整 Theme 只在私有 Runtime Boundary 内加载。

## 已有生产流程

GUIF 继续提供：

- 私有 Versioned Theme Library 与 Conversation-first Theme Selection；
- Workflow-driven Planner、Director、Theme、Resource、Prompt 与 Semantic QA Agent；
- 可配置 Host / Tool 路由与 ChatGPT 默认值；
- Artifact Identity、Immutable Reference、SHA-256、MIME 与 Dimension；
- Deterministic Metadata Review 与可选 Semantic Visual Inspector；
- Controlled Revision Execution 与 Review-gated Supersession；
- Gated Export、Engine Manifest、Transaction Audit、Backup 与 Rollback；
- 带 Plan、Diff、Branch、Commit 和 Revert 的 Task-bound Git Change Set；
- Current-tree Privacy Audit 与 Legacy Theme Migration。

## 命令入口

```text
guif          Framework、Theme、Task、Artifact、QA、Revision 与 Export
guif-ops      Credential、Lease、Callback、Approval、Export 与 Git Authenticated Operation
guif-gateway  Authenticated HTTP Host Boundary
guif-ledger   Private Operation Ledger 检查与验证
```

`guif-ops` 默认从 `GUIF_HOST_TOKEN` 与 `GUIF_TASK_LEASE` 读取 Token，避免进入命令历史。

## 开发

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## 当前限制

- Gateway 使用本地 GUIF Bearer Credential；尚未实现 OIDC、mTLS Client Identity、Hardware-backed Key 和 Remote Identity Provider。
- 内置 WSGI Server 适合作为受控单机 Boundary，不应直接作为公网 Edge 暴露。
- Task Lease 与 Ledger Lock 仍是 Process-local / File-backed，不是分布式协调原语。
- 旧版未认证 Runtime API 为兼容性继续存在，可绕过 alpha.25 的认证和 Ledger 保证。
- Operation Ledger 使用私有对称 HMAC Key，不是公开签名或外部不可变审计服务。
- ChatGPT 产品侧仍需配置为自动调用 Gateway Endpoint。
- 默认 Semantic Visual Inspector Registry 仍为空。
- Private Storage 尚无静态加密、远程同步、Retention Policy 和灾难恢复复制。
- Git Execution 只创建本地 Branch 与 Commit；尚未自动 Push、创建 PR 或处理 Protected Branch。
- Current-tree Privacy Audit 无法证明 Git History、Fork、Cache 或外部 Clone 已被清理。

## 下一阶段

下一优先级是 **alpha.26：Real ChatGPT Image Loop 与 Default Visual Inspector**：Host 侧自动消费 Handoff、执行图片生成/修图、通过 Gateway 自动回传、默认 Semantic Visual Inspection、Revision Retry Orchestration，以及完整可运行的 End-to-end Project Acceptance Test。
