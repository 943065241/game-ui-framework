# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，默认语义视觉检查器是 `chatgpt-vision`；三者都是可替换契约，不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-alpha.26` 新增可领取的 ChatGPT-first Host 工作闭环，用于真实图片生成、图片修图和语义视觉检查。

```text
选择私有 Theme
  -> Prompt / Approval / Tool Handoff
  -> 图片生成或图片修图 Host Work
  -> Authenticated Claim + Task Lease
  -> Host 真正调用图片 Tool
  -> Artifact Registration
  -> Deterministic Metadata Review
  -> chatgpt-vision Semantic Inspection Work
  -> passed / review-required / blocked
  -> 需要时生成 Controlled Revision Job
  -> Gated Export / Git Change Set
```

中英文持续迭代规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。隐私迁移和仓库历史处理说明见 [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md)。

## alpha.26 已经可以运行的内容

持久化的 `chatgpt-image` Handoff 现在会成为私有 Host Work：

```text
image-generation
image-editing
visual-inspection
```

每个 Work Item 包含：

- Project、Task、Tool、Handoff 和 Artifact Identity；
- 已批准的 Prompt Job 或 Visual Inspection Request；
- Required Capability 与 Submission Contract；
- 具有 SHA-256 Identity 的不可变可下载 Attachment；
- `available / claimed / completed` 状态；
- 绑定 Authenticated Actor 的一次性 Claim Secret；
- 与 Artifact 或 Visual Review 关联的 Result Receipt。

Work Record 保存在框架 Git 和 Project Git 之外：

```text
<private-data-root>/host-work/<project>/work-*.json
```

持久化 Record 不保存原始 Claim Token。

## Production Gateway 工作流

启动 Gateway：

```bash
pip install -e .[dev]
guif-gateway --workspace . --host 127.0.0.1 --port 8765
```

绑定远程地址仍需要显式启用并配置 TLS：

```bash
guif-gateway \
  --host 0.0.0.0 \
  --port 8765 \
  --allow-remote \
  --tls-cert server.crt \
  --tls-key server.key
```

创建具备 Host Work Capability 的 Credential：

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
        "host-work:read",
        "host-work:claim",
        "host-work:complete",
        "task:lease",
        "tool-result:submit",
        "visual-inspection:submit",
        "export:execute",
    ),
)

bearer_token = issued["bearer_token"]  # 只显示一次
```

### 发现 Work

```http
GET /v1/work?project=SampleGame&status=available
Authorization: Bearer guifh1....
```

### 领取 Work

```http
POST /v1/work/SampleGame/work-image-123/claim
Authorization: Bearer guifh1....
Content-Type: application/json
Idempotency-Key: claim-001

{"ttl_seconds": 300}
```

响应只返回一次 `guifw1.<work-id>.<secret>`。Claim Ownership 与 Authenticated Actor 和 Credential 绑定。

### 下载不可变 Attachment

```http
GET /v1/work/SampleGame/work-visual-123/attachments/attachment-456
Authorization: Bearer guifh1....
X-GUIF-Work-Claim: guifw1....
```

返回文件前，GUIF 会重新检查路径边界、文件存在性和 SHA-256。图片修图 Work 可以通过该接口取得不可变 Source Artifact；Visual Inspection Work 可以取得待检查 Artifact。

### 提交真实图片结果

先通过既有 `/lease` Endpoint 获取 Task Lease，再提交原始图片 Bytes：

```http
POST /v1/work/SampleGame/work-image-123/result
Authorization: Bearer guifh1....
Idempotency-Key: image-result-001
If-Match: "task-sha256:..."
X-GUIF-Lease-Token: guifl1....
X-GUIF-Work-Claim: guifw1....
X-GUIF-Filename: fictional-screen.png
X-GUIF-Content-SHA256: <sha256>
X-GUIF-Width: 1080
X-GUIF-Height: 2340
X-GUIF-Model-ID: chatgpt-image
Content-Type: image/png

<raw PNG bytes>
```

结果会经过 Authenticated Callback Contract 登记。随后 GUIF 自动检查 Artifact Eligibility、File Integrity、Dimension、Format、Alpha 和 Registered Metadata。Metadata Review 通过后，会自动创建 `visual-inspection` Work。

### 提交语义视觉检查结果

```http
POST /v1/work/SampleGame/work-visual-123/result
Authorization: Bearer guifh1....
Idempotency-Key: visual-result-001
If-Match: "task-sha256:..."
X-GUIF-Lease-Token: guifl1....
X-GUIF-Work-Claim: guifw1....
Content-Type: application/json

{
  "inspector_id": "chatgpt-vision",
  "status": "review-required",
  "summary": "层级需要受控修改。",
  "findings": [
    {
      "id": "hierarchy-1",
      "severity": "review",
      "category": "composition-and-hierarchy",
      "code": "primary-action-too-weak",
      "message": "增强虚构主操作入口的视觉层级。",
      "evidence": {"region": "lower-center"}
    }
  ]
}
```

允许的 Status：

```text
passed
review-required
blocked
```

只有在收到经过认证的 Inspector Result 后，GUIF 才会声明语义视觉结论。Metadata 不能被当成语义视觉通过。

存在可执行 Finding 时，GUIF 会自动创建 Versioned Revision Job。Revision Job 仍处于 `approval-pending`；初始生成 Approval 不会自动授权后续修图。

## 可嵌入的 ChatGPT Host Loop

Host 集成也可以不通过 HTTP，而是提供真实的图片和视觉 Callable：

```python
from guif.chatgpt_host_loop import ChatGPTHostLoop

loop = ChatGPTHostLoop(runtime, bearer_token=bearer_token)

loop.run_once(
    "SampleGame",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

`ChatGPTHostLoop` 负责 Work Discovery、Task Etag、Task Lease、Claim Ownership、Immutable Attachment Retrieval、Result Submission、Artifact Registration 和失败时的 Lease Release。传入的 Callable 负责真正生成或修改 Pixel，以及执行语义视觉检查。

## 重要执行边界

本地 Python Package 无法自行调用 ChatGPT 内部图片 Tool。alpha.26 提供的是生产 Work Queue、Authenticated Transport、Attachment Binding 和可嵌入 Host SDK，由 ChatGPT 或其他 Host 调用自身 Tool 后回传结果。

因此：

```text
GUIF 不伪造图片 Pixel。
GUIF 不根据 Metadata 伪造语义视觉通过。
dry-run 不会成为生产任务的静默回退。
Host 必须提供真实图片与视觉能力。
```

## 私有数据边界

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

真实用户 Theme、对话决策、Prompt、Work Claim、Attachment、Runtime Evidence、Callback Receipt 和 Semantic Finding 默认都不会进入框架 Git 或 Project Git。公共测试和示例只使用完全虚构的 Fixture。

## 继续保留的生产控制

GUIF 继续提供：

- Private Versioned Theme Library 与 Conversation-first Theme Selection；
- Configurable Host / Tool Discovery、Connection 与 Routing；
- Contract QA 与 Persistent Approval Gate；
- Artifact Identity、SHA-256、MIME、Dimension 与 Immutable Reference；
- Controlled Revision Execution 与 Review-gated Supersession；
- Gated Export、Engine Manifest、Backup、Rollback 与 Git Change Set；
- Authenticated Actor、Task Etag、Exclusive Lease、Idempotency 与 Signed Private Operation Evidence；
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

- ChatGPT 产品侧仍需要嵌入 `ChatGPTHostLoop` 或消费 Gateway Work Endpoint；仓库自身不能接入 ChatGPT 内部 Tool Runtime。
- 默认 Semantic Inspector 是经过认证的外部结果契约，不是本地自主视觉模型。
- Work Claim 和 Task Lease 是 File-backed 本地协调，不是分布式一致性锁。
- 内置 WSGI Server 是单节点 Host Boundary，不是互联网边缘反向代理。
- Private Storage 尚未提供静态加密、远程同步、Retention Policy 或多设备冲突处理。
- 尚未自动执行 Remote Git Push、PR 创建、Protected Branch 协商和 Server-side Check 编排。
- Current-tree Privacy Audit 无法证明 Git History、Fork、Cache 或外部 Clone 已被清理。

## 下一阶段

下一优先级是 **alpha.27：Conversation-first User Workflow and Recovery**：一键初始化、Conversation Session State、自动 Theme 确认、Project 选择、生成与修图进度、失败 Work 恢复、私有备份和 Schema Migration，以及不向用户暴露 Task ID、Etag、Lease、Claim 或 Callback ID 的使用流程。
