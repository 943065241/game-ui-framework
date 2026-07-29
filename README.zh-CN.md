# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，默认语义视觉检查器是 `chatgpt-vision`；三者都是可替换契约，不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-alpha.27` 新增私有的 Conversation-first Workflow。正常用户流程不再暴露 Task ID、Etag、Lease、Work Claim、Handoff 或 Callback。

```text
开始对话
  -> 确认、创建、派生或明确跳过私有 Theme
  -> 用自然语言描述需要设计的界面
  -> 审阅并批准生成契约
  -> ChatGPT Host 执行图片生成或修图
  -> 确定性图片 Metadata Review
  -> chatgpt-vision 语义视觉检查
  -> 必要时单独批准返修
  -> Gated Export
```

中英文持续迭代规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。隐私迁移和仓库历史处理说明见 [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md)。

## 对话式 API

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
issued = runtime.register_host_credential(
    actor_id="conversation-host",
    host_id="chatgpt",
    capabilities=(
        "approval:decide",
        "export:execute",
        "host-work:read",
        "host-work:claim",
        "host-work:complete",
        "revision:decide",
        "task:lease",
        "task:resume",
        "tool:execute",
        "tool-result:submit",
        "visual-inspection:submit",
    ),
)

conversation = runtime.conversation_workflow(
    bearer_token=issued["bearer_token"],
)

view = conversation.open(
    "SampleGame",
    "conversation-001",
)
```

默认用户视图只包含：

```text
conversation_id
project
stage
message
Theme 摘要
当前可执行操作
安全的 Artifact 摘要
恢复状态
```

默认不会包含 Task ID、Task Etag、Lease Token、Work Claim Token、Handoff ID、Callback ID、私有文件路径或完整 Theme 内容。只有开发和支持场景显式启用 Diagnostics 时才会返回底层标识。

## Theme 确认

没有私有 Theme Binding 的新对话首先进入：

```text
theme-confirmation
```

```python
view = conversation.create_theme(
    "SampleGame",
    "conversation-001",
    "Fictional Orbital Fixture",
    {
        "description": "A wholly fictional orbital kiosk interface.",
        "palette": ["test violet", "test silver"],
        "materials": ["matte composite"],
        "lighting": "soft synthetic daylight",
        "must_include": ["circular menu"],
        "avoid": ["real brands"],
    },
)
```

支持以下路径：

```text
select_theme       选择历史私有 Theme
create_theme       创建并绑定新 Theme
derive_theme       创建并绑定新的不可变 Theme Version
continue_unbound   明确确认本次对话不绑定 Theme
```

真实 Theme 内容继续保存在框架 Git 和 Project Git 之外的 Private Theme Library。

## 提交自然语言需求

```python
view = conversation.submit(
    "SampleGame",
    "conversation-001",
    "Create a 1080x2340 fictional orbital shop page and export Unity",
    request_key="chat-turn-001",
)
```

`request_key` 提供幂等性。同一个 Key 与同一需求会返回已有状态；同一个 Key 被用于不同内容时会 Fail Closed，不会重复创建 Task。

初次提交通常进入：

```text
approval-required
```

无需处理 Approval ID 或 Task Lease：

```python
view = conversation.approve(
    "SampleGame",
    "conversation-001",
    comment="Proceed with the approved production contract.",
)
```

Service 会自动识别当前 Approval Context、获取并消费 Private Lease、记录 Authenticated Actor，并准备正确的图片 Work。

## 真实图片与视觉闭环

ChatGPT 产品或其他配置后的 Host 提供真正的 Tool Callable：

```python
view = conversation.run_host_until_blocked(
    "SampleGame",
    "conversation-001",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

Service 会将执行范围限制在当前对话的 Active Task，并自动处理：

```text
Host Work Discovery
-> Task Etag
-> Exclusive Task Lease
-> 绑定 Actor 的一次性 Work Claim
-> Immutable Attachment Retrieval
-> Image 或 Semantic Result Submission
-> Artifact Registration
-> Metadata Review
-> Semantic Review
-> 下一个用户可理解状态
```

该调用不会消费其他对话的 Work。

Semantic Result 允许：

```text
passed
review-required
blocked
```

Metadata 仍然不能被当作语义视觉通过。

## 受控返修

存在可执行 Semantic Finding 时，会形成 Revision Plan 和 Versioned Revision Job。初始图片生成 Approval 不会授权后续修图。

用户状态变为：

```text
revision-approval-required
```

此时调用 `conversation.approve(...)` 只批准当前 Revision，并准备 `image-editing` Work。原 Artifact 在 Replacement 通过语义视觉检查前继续保持 Active。

## Gated Export

Contract QA 与全部 Active Visual Artifact 通过后，状态变为：

```text
ready-to-export
```

```python
view = conversation.export(
    "SampleGame",
    "conversation-001",
    target_engine="unity",
)
```

Service 会自动获取 Export Lease 并调用既有 Authenticated Gated Export。对话式入口不会绕过 Engine Manifest、Transaction Evidence、Backup、Rollback 或 Git Change Control。

## 恢复机制

Conversation Record 与 Checkpoint 保存在私有目录：

```text
<private-data-root>/conversation-workflows/<project>/conversation-<sha256>.json
```

每个 Checkpoint 记录用户可理解 Stage、持久化 Task Status、Task Etag、Artifact Count 和时间戳。原始 Secret 永远不会写入 Conversation Record。

```python
view = conversation.recover("SampleGame", "conversation-001")
```

Recovery 会重新协调 Private Conversation Record、Persisted Task 和 Host Work。Session 中丢失的 Task Reference 可以根据 Task 的 Private Conversation Binding 恢复。Pipeline 失败后可通过 `conversation.retry(...)` 从已保存的 Agent Checkpoint 继续。

## 命令行工作流

Host Token 只需在环境变量中配置一次：

```bash
export GUIF_HOST_TOKEN='guifh1....'
```

随后使用对话级命令：

```bash
guif-conversation open \
  --project SampleGame \
  --conversation conversation-001

guif-conversation theme-list \
  --project SampleGame \
  --conversation conversation-001

guif-conversation submit \
  --project SampleGame \
  --conversation conversation-001 \
  --request-key chat-turn-001 \
  "Create a fictional orbital shop page and export Unity"

guif-conversation approve \
  --project SampleGame \
  --conversation conversation-001

guif-conversation status \
  --project SampleGame \
  --conversation conversation-001

guif-conversation recover \
  --project SampleGame \
  --conversation conversation-001
```

CLI 不会内置虚假的图片模型。真正的图片与视觉执行仍来自配置后的 Host Tool 集成或 Authenticated Gateway Work Endpoint。

## 私有数据边界

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

真实 Theme、Prompt、对话决策、Work Claim、Attachment、Artifact、Finding 和 Runtime Evidence 默认不会进入框架 Git 或 Project Git。公共测试和示例只使用完全虚构的 Fixture。

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

- ChatGPT 产品侧仍需要嵌入 Conversation/Host Loop 或消费 Gateway Work Endpoint；仓库自身不能接入 ChatGPT 内部 Tool Runtime。
- Semantic Inspector 是经过认证的外部结果契约，不是本地自主视觉模型。
- Conversation、Work 和 Task 使用 File-backed 本地协调，不是分布式一致性系统。
- Private Storage 尚未提供静态加密、远程同步、Retention Policy 或多设备冲突处理。
- Conversation CLI 可以维护状态和审批，但独立终端无法直接调用 ChatGPT 内部图片 Tool。
- Current-tree Privacy Audit 无法证明 Git History、Fork、Cache 或外部 Clone 已被清理。

## 下一阶段

下一优先级是 **alpha.28：Usability Freeze and Beta Readiness**：一键 Onboarding、私有 Backup/Restore、Schema Migration、失败诊断、端到端样例验证、兼容性保证，以及在 `beta.1` 前冻结 MVP Scope。
