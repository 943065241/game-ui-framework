# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，默认语义视觉检查器是 `chatgpt-vision`；三者都是可替换契约，不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-alpha.28` 冻结面向对话的 MVP，并补齐 Beta 就绪控制：

```text
一条命令完成初始化
  -> 确认私有 Theme
  -> 自然语言提交生产需求
  -> 上下文审批
  -> 真实图片生成或修图
  -> 确定性 Metadata Review
  -> 语义视觉检查
  -> 必要时单独审批 Revision
  -> Gated Export
  -> 已校验的私有备份与恢复
```

alpha.28 不再扩张大型子系统，而是稳定 alpha.27 的日常流程，为私有数据建立明确的备份、迁移和恢复契约，并定义 beta.1 必须保持的兼容边界。

中英文持续迭代规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。隐私迁移和仓库历史处理说明见 [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md)。

## 一条命令完成初始化

安装开发版本：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

初始化 Project、创建 ChatGPT Host Credential，并打开私有 Conversation：

```bash
guif-ready start \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

第一次执行可以创建：

```text
projects/SampleGame/project.json
私有 Host Credential
私有 Conversation Workflow Record
Theme 确认视图
```

新签发的 Bearer Token 只显示一次，应保存到受保护的 Secret Manager 或环境变量：

```bash
export GUIF_HOST_TOKEN='guifh1....'
```

Token 不会写入 Project Git、Conversation Record、Backup Manifest、Diagnostic Report 或公共输出。

## Conversation-first 工作流

完成初始化后，通过既有对话入口继续：

```bash
guif-conversation open \
  --project SampleGame \
  --conversation conversation-001
```

新 Conversation 首先进入：

```text
theme-confirmation
```

支持的 Theme 路径：

```text
theme-list       查看私有历史主题
theme-select     选择历史 Theme
theme-create     创建并绑定新 Theme
theme-derive     派生不可变的新 Theme Version
theme-unbound    明确本次不绑定 Theme
```

真实用户 Theme 内容只保存在框架 Git 和 Project Git 之外的私有 Theme Library。公共仓库示例只使用完全虚构的 Fixture。

提交自然语言需求：

```bash
guif-conversation submit \
  --project SampleGame \
  --conversation conversation-001 \
  --request-key chat-turn-001 \
  "创建一个虚构的 1080x2340 天文台商店页面并导出 Unity"
```

批准当前 Initial 或 Revision Gate 时，不需要手动处理 Approval ID、Task ID、Etag、Lease、Claim、Handoff ID 或 Callback ID：

```bash
guif-conversation approve \
  --project SampleGame \
  --conversation conversation-001
```

默认用户视图只包含：

```text
Conversation 与 Project
当前 Stage 与提示信息
私有 Theme 摘要
上下文操作
安全的 Artifact 摘要
恢复状态
```

底层 Identity 和并发控制仍然严格执行，只会在显式 Diagnostics 或开发者 API 中显示。

## 真实图片与视觉闭环

由配置后的 Host 提供真实图片与视觉能力：

```python
view = conversation.run_host_until_blocked(
    "SampleGame",
    "conversation-001",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

GUIF 自动协调：

```text
限定当前 Task 的 Host Work Discovery
-> Task Etag
-> Exclusive Task Lease
-> 绑定 Actor 的一次性 Work Claim
-> Immutable Attachment Retrieval
-> 提交真实图片或语义结果
-> Artifact Registration
-> Metadata Review
-> Semantic Review
-> 推导下一用户阶段
```

本地 Python Package 不会伪造 Pixel，也无法自行进入 ChatGPT 产品内部调用图片 Tool。ChatGPT 或其他配置 Host 必须嵌入 Host Loop，或消费 Authenticated Gateway Work API。

Metadata Review 不能声称 Theme 一致性、构图、可读性或可用性已经通过，这些结论必须来自经过认证的 Semantic Visual Result。

## Controlled Revision

存在可执行视觉 Finding 时，会创建 Versioned Revision Job 和独立 Approval Gate：

```text
revision-approval-required
```

初始生成 Approval 不会自动授权修图。Source Artifact 会持续有效，直到 Replacement 是真实非模拟图片、Lineage 有效，并通过最终语义视觉检查。

## 已校验的私有备份

创建默认 Portable Backup：

```bash
guif-ready backup --workspace .
```

默认保存位置：

```text
<private-data-root>/backups/portable-<timestamp>.guif-private.zip
```

Portable Profile 包含用户拥有和可恢复的生产数据，例如：

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

默认明确排除：

```text
Host Credential 与 Credential Verifier
Operation Ledger Signing Key
Gateway Request Receipt
Operation Audit 中的认证材料
```

`full-local` Archive 必须显式确认包含敏感材料：

```bash
guif-ready backup \
  --workspace . \
  --profile full-local \
  --include-sensitive \
  --output /protected/offline/location/full-local.guif-private.zip
```

GUIF Backup 提供完整性校验，但当前不提供静态加密。包含敏感材料的 Archive 必须存放在受保护的加密介质或加密备份系统中。

### Backup Verification

```bash
guif-ready backup-verify /path/to/portable.guif-private.zip
```

校验内容：

```text
Manifest Schema 与 Manifest Hash
Canonical Member Path
禁止 Path Traversal
禁止重复 Member
禁止 Symbolic Link Member
逐文件 Size 与 SHA-256
总解压大小限制
禁止未登记的 Archive Member
```

### Plan-first Restore

Restore 默认只生成计划，不修改文件：

```bash
guif-ready backup-restore /path/to/portable.guif-private.zip
```

Conflict Policy：

```text
fail      出现不同现有文件时阻止
skip      保留现有冲突文件
replace   先创建 Portable Pre-restore Backup，再替换冲突文件
```

显式执行：

```bash
guif-ready backup-restore \
  /path/to/portable.guif-private.zip \
  --conflict replace \
  --apply
```

Restore 对每个文件使用原子写入，并在落盘后重新校验 SHA-256。

## 有记录的私有 Schema Migration

只扫描、不修改：

```bash
guif-ready migrate --workspace .
```

显式应用受支持的修复：

```bash
guif-ready migrate \
  --workspace . \
  --apply \
  --actor local-owner
```

alpha.28 保持 Conversation Workflow Schema Version 1 兼容，同时补齐冻结 MVP 所需的 Privacy 与 Compatibility Metadata。每次修复都会写入 Private Migration History 和独立 Migration Report。

未知未来 Schema、无效 JSON 和疑似 Raw Secret Field 会 Fail Closed，需要人工处理。

## Privacy-safe Diagnostics

```bash
guif-ready diagnose \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

Diagnostics 检查：

```text
Project 结构与 Schema
Private Storage 可用性
Private Schema Migration 状态
Operation Ledger 完整性
Host Credential Capability
Conversation Stage 与 Recovery
Portable Backup 是否存在
冻结的 Compatibility Contract
```

默认报告不会暴露 Task ID、Etag、Lease Token、Claim Token、Handoff ID、Callback ID、Bearer Token 或 Private Storage Path。持久化报告保存在：

```text
<private-data-root>/diagnostics/<project>/
```

## End-to-end Acceptance Gate

```bash
guif-ready acceptance \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

只有满足以下条件才通过：

```text
不存在 Blocking Readiness Check
并且
Conversation Stage 为 ready-to-export 或 completed
```

使用 `--require-completed` 可以要求最终 Gated Export 已完成。

Acceptance 不会生成虚假图片，也不会把只通过 Metadata 的 Artifact 当作视觉验收完成。

## 冻结的 alpha.28 Compatibility Contract

```bash
guif-ready contract
```

Public API Version 为 `1`。beta.1 必须保持冻结的 Conversation Stage 与 Action；如需破坏性修改，必须增加新的 Public API Version，并提供明确迁移路径。

冻结的用户阶段包括：

```text
theme-confirmation
ready-for-request
approval-required
ready-to-produce
image-production
visual-review
revision-approval-required
revision-ready
tool-configuration-required
ready-to-export
completed
recoverable-error
attention-required
```

显式 Legacy `ProviderAdapter` 仍作为兼容路径保留。生产 Tool Routing 继续默认 ChatGPT-first 且可配置；`dry-run` 只用于测试和开发，绝不会成为生产任务的静默回退。

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
  operation-audit/
  operation-ledger/
  backups/
  diagnostics/
  runs/
  plans/
  migrations/
  privacy-reports/
```

真实 Theme、Prompt、Conversation Decision、Approval Evidence、Runtime State、Work Claim、Attachment、图片文件、Semantic Finding、Credential、Backup Archive 和 Diagnostic Report 默认都不会进入框架 Git 或 Project Git。

## 继续保留的生产控制

GUIF 继续提供：

- 私有、可版本化 Theme Library 与 Conversation Binding；
- 可配置 Host / Tool Discovery、Connection、Health 与 Routing；
- Model-neutral Prompt IR、Contract QA 与 Persistent Approval Gate；
- Artifact Identity、SHA-256、MIME、Dimension、Immutable Reference 与 Provenance；
- 经过认证的图片生成、修图与 Semantic Visual Inspection Work；
- Controlled Revision Execution 与 Review-gated Supersession；
- Gated Export、Engine Manifest、Backup、Rollback 与 Git Change Set；
- Authenticated Actor、Task Etag、Exclusive Lease、Idempotency 与 Signed Private Operation Evidence；
- Current-tree Privacy Audit 与 Legacy Theme Migration。

## 开发

```bash
pytest -q
```

CI 覆盖 Python 3.10、3.11 和 3.12。

## 当前限制

- ChatGPT 产品侧仍需嵌入 `ChatGPTHostLoop` 或消费 Gateway Work API；仓库本身不能调用 ChatGPT 内部图片 Tool。
- Portable Archive 提供完整性校验，但未加密。
- File-backed Work Claim 与 Task Lease 是单节点协调，不是分布式一致性机制。
- 内置 WSGI Gateway 不是互联网边缘反向代理。
- 远程私有数据同步、Retention Policy、Key Rotation 和多设备冲突处理尚未实现。
- Current-tree Privacy Audit 无法证明 Git History、Fork、Cache 或外部 Clone 已被清理。
- Remote Git Push、Protected Branch 协商与 Server-side Release Orchestration 仍不属于本地 Core。

## 下一阶段

下一目标是 **beta.1：在不扩张冻结 MVP 的前提下完成生产加固**。重点包括加密备份集成边界、从支持的 Alpha Version 升级测试、性能与故障注入测试、正式打包安装、Release Notes 和明确的 Support Window。
