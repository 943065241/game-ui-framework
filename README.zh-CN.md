# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，但二者都不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-alpha.24` 新增经过认证的 Host 操作、Task 乐观并发、独占 Task Lease、稳定 External Result Callback，以及与 Task 绑定的 Git Change Set。

```text
选择私有 Theme
  -> Prompt / Approval / Tool Handoff
  -> Authenticated Host Actor
  -> Optimistic Task Etag
  -> Expiring Exclusive Task Lease
  -> Authenticated Result Callback
  -> Artifact / Review / Revision / Gated Export
  -> Reviewable Git Change Set
  -> Dedicated Branch + Commit
  -> Optional Revert Commit
```

中英文双语产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。隐私迁移和 Git 历史处理指引见 [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md)。

## Authenticated Host Actor

Host Credential 是存放在框架 Git 和 Project Git 之外的私有本地记录。注册时只返回一次 Bearer Token。GUIF 只保存 PBKDF2-HMAC-SHA256 Verifier，不保存原始 Secret。

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
issued = runtime.register_host_credential(
    actor_id="production-host",
    host_id="chatgpt",
    capabilities=(
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

Credential Metadata 会记录 Actor、Host、Role、Capability、Issuer、生命周期和可选过期时间。Credential 可以列出、吊销或轮换，但不会暴露 Secret Verifier。

经过认证的操作会保存标准化 Actor Snapshot：

```json
{
  "actor_id": "production-host",
  "host_id": "chatgpt",
  "credential_id": "cred-...",
  "capabilities": ["task:lease", "tool-result:submit"],
  "authenticated": true
}
```

## Task 乐观并发

每个持久化 Task 都有确定性的 Etag：

```python
etag = runtime.get_task_etag("SampleGame", task_id)
```

写操作发现 Etag 已过期时会拒绝执行，不会静默覆盖更新后的 Task State。

执行独占操作前先获取有过期时间的 Lease：

```python
lease = runtime.acquire_task_lease(
    "SampleGame",
    task_id,
    bearer_token=bearer_token,
    expected_task_etag=etag,
    ttl_seconds=300,
    purpose="host-result-callback",
)

lease_token = lease["lease_token"]  # 只显示一次
```

Lease 会绑定：

- Project 与 Task Identity；
- Authenticated Actor 与 Credential；
- Base Task Etag；
- Operation Purpose；
- Acquire 与 Expire 时间；
- Consumed、Released 或 Expired 生命周期。

同一 Task 的第二个 Active Lease 会被拒绝。写操作成功后会消费 Lease。Stale Task、Expired Lease、错误 Actor、错误 Credential 和被篡改的 Lease Token 都会 Fail Closed。

## 稳定的 Authenticated Host Callback

旧版 `submit_tool_result()` API 继续保留兼容性。生产 Host 集成应使用 `submit_authenticated_tool_result()`。

```python
content = Path("generated-screen.png").read_bytes()

task = runtime.submit_authenticated_tool_result(
    "SampleGame",
    task_id,
    handoff_id,
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    content=content,
    filename="generated-screen.png",
    mime_type="image/png",
    width=1080,
    height=2340,
    model_id="image-model",
)
```

Callback 会校验：

- Host Credential 与 `tool-result:submit` Capability；
- Host Identity 是否与持久化 Handoff 一致；
- Tool 与 Execution Identity；
- Active Lease Ownership；
- Expected Task Etag；
- Content SHA-256；
- Handoff Status 与幂等 Callback Identity。

完成后的 Callback Record 会写入 `host-callbacks.json`，并关联 Actor、Lease、Envelope、Execution、Handoff、Content Hash 和最终 Artifact。

## Authenticated Approval 与 Export

Approval 和生产写入可以使用同一套 Identity 与 Lease Boundary：

```python
task = runtime.decide_approval_authenticated(
    "SampleGame",
    task_id,
    approval_id,
    "approved",
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    comment="已根据批准的 Contract 完成审阅。",
)
```

```python
record = runtime.execute_gated_export_authenticated(
    "SampleGame",
    task_id,
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    target_engine="unity",
)
```

Approval 与 Export Record 会附加 Authenticated Actor 和 Lease Evidence。原有仅接收字符串 Actor 的 API 继续作为兼容路径存在，但不具备 alpha.24 的认证保证。

## Task-bound Git Change Set

完成后的 Gated Export 可以转换为可审阅的 Git Change Set。Prepare 阶段不会创建 Branch 或 Commit。

```python
change = runtime.prepare_export_git_change(
    "SampleGame",
    task_id,
    export_id,
    bearer_token=bearer_token,
    expected_task_etag=etag,
    branch_name="guif/sample-game/export-001",
)

diff = runtime.diff_git_change(
    "SampleGame",
    task_id,
    change["change_set_id"],
)
```

Plan 会记录：

- Repository Root 与 Project Root；
- Source Task 与 Completed Export；
- Export Transaction SHA-256；
- Base Git HEAD 与 Branch；
- 选中的 Project Truth、Engine Output 和 Transaction Path；
- Proposed Branch 与 Commit Message；
- Working Tree Status。

审阅后，获取新的 Lease 并执行：

```python
committed = runtime.execute_git_change(
    "SampleGame",
    task_id,
    change["change_set_id"],
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
)
```

GUIF 会确认 Git HEAD 仍与 Plan 一致，创建独立 Branch，只 Stage 选中的 Path，生成 Commit，记录 Staged Diff Hash，并将 Commit 关联回 Gated Export。

已提交的 Change Set 可以生成普通 Git Revert Commit：

```python
reverted = runtime.revert_git_change(
    "SampleGame",
    task_id,
    change["change_set_id"],
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    reason="恢复之前批准的 Project State。",
)
```

如果选中的 Path 存在更新的未提交修改，Revert 会 Fail Closed。

## Operational CLI

alpha.24 新增独立的 `guif-ops` 入口，让 Bearer Token 与 Lease Token 通过环境变量传递，避免直接进入命令历史。

```bash
pip install -e .[dev]

guif-ops credential-create production-host chatgpt \
  task:lease tool-result:submit approval:decide \
  export:execute git:prepare git:commit git:revert

export GUIF_HOST_TOKEN='guifh1....'

guif-ops task-etag <task-id> --project SampleGame

guif-ops lease-acquire <task-id> \
  --project SampleGame \
  --expected-etag 'task-sha256:...'

export GUIF_TASK_LEASE='guifl1....'

guif-ops callback-submit <task-id> <handoff-id> generated.png \
  --project SampleGame \
  --expected-etag 'task-sha256:...'
```

其他命令包括：

```text
credential-list / credential-revoke / credential-rotate
lease-show / lease-renew / lease-release
callback-list / callback-show
approval-decide
export-execute / export-rollback
git-plan / git-list / git-show / git-diff / git-commit / git-revert
summary
```

## 私有数据目录

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  project-theme-bindings/
  host-credentials/
  runs/<project>/<task-id>/
    task.json
    task-lease.json
    host-callbacks.json
    git-changes.json
  plans/
  migrations/
  privacy-reports/
```

完整 Theme Content、Host Credential Verifier、Task Lease、Callback Evidence、自然语言 Plan 和 Runtime Evidence 默认都不会进入框架 Git 或 Project Git。

## 已有生产流程

GUIF 继续提供：

- 私有 Versioned Theme Library 与 Conversation-first Theme Selection；
- Workflow-driven Planner、Director、Theme、Resource、Prompt 与 Semantic QA Agent；
- 可配置 Host / Tool 路由与 ChatGPT 默认集成；
- Artifact Identity、Immutable Reference、SHA-256、MIME 与 Dimension；
- Deterministic Metadata Review 与可选 Semantic Visual Inspector；
- Controlled Revision Execution 与 Review-gated Supersession；
- Gated Export、Engine Manifest、Transaction Audit、Backup 与 Rollback；
- Current-tree Privacy Audit 与 Legacy Theme Migration。

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

- Host Credential 是本地 Bearer Credential；尚未实现 OIDC、mTLS、Hardware-backed Key 和 Remote Identity Provider。
- Task Lease 是 Private Store 中的逻辑 Lease，不是操作系统锁或分布式锁；旧版未认证 API 可以绕过它。
- Git Change Set 依赖本地 Git、Named Current Branch 和已经配置的 Git Author Identity。
- Git Execution 只创建本地 Branch 与 Commit；尚未自动 Push Remote、创建 PR、协商 Protected Branch 或等待 Server-side Check。
- Callback Content 通过本地 Runtime API 或 CLI 提交；当前不包含 Network Callback Server。
- Private Storage 仍为 File-backed，尚无静态加密、远程同步和 Retention Policy。
- 默认 Semantic Visual Inspector Registry 为空。
- Current-tree Privacy Audit 无法证明 Git History、Fork、Cache 或外部 Clone 已被清理。

## 下一阶段

下一优先级是 **alpha.25：Production Host Gateway 与 Signed Operation Ledger**，包括 Network Callback Transport、OIDC 或可插拔 Identity Verification、Cross-process Lock、Signed Callback / Export Receipt、Remote Git Push / PR Integration、Protected Branch Check 和 Durable Operation Recovery。
