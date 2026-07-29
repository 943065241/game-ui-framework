# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，默认语义视觉检查器是 `chatgpt-vision`；三者都是可替换契约，不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-beta.2` 是冻结 Conversation MVP 的维护与 Provenance 加固版本：

```text
一条命令完成初始化
  -> 确认私有 Theme
  -> 自然语言提交生产需求
  -> 上下文 Approval
  -> 真实图片生成或修图
  -> 确定性 Metadata Review
  -> 语义视觉检查
  -> 必要时单独审批 Revision
  -> Gated Export
  -> 已校验的私有备份与恢复
  -> 可选的外部备份保护
  -> 有记录的 alpha 到 beta 升级保障
  -> 非变更型 Soak Profile
  -> 可验证的 Wheel / sdist Hash Provenance
```

beta.2 保持 Public API Version `1`，并继续兼容 alpha.28 冻结的全部 Conversation Stage 与 Action。Python Package Version 为 `1.0.0b2`。

重要文档：

- [持续迭代产品规格](docs/GUIF_PRODUCT_SPEC.md)
- [beta.2 Release Notes](docs/RELEASE_NOTES_BETA2.md)
- [beta.2 Security Review](docs/SECURITY_REVIEW_BETA2.md)
- [beta.1 Release Notes](docs/RELEASE_NOTES_BETA1.md)
- [Support Policy](SUPPORT.md)
- [Privacy Migration Guidance](docs/PRIVACY_MIGRATION.md)

## 安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

CI 会在 Python 3.10、3.11、3.12 上运行测试，并把 Pillow 弃用 Warning 当作错误；随后构建 Wheel 与 Source Distribution、生成并校验 Hash Provenance、安装生成的 Wheel、校验 `guif.__version__`，最后执行 CLI Contract Smoke Test。

## Release Artifact Provenance

构建两种正式产物：

```bash
python -m build
```

生成绑定 Git Commit 与 Package Metadata 的机器可读 SHA-256 Manifest：

```bash
guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <40-or-64-character-hex-commit>
```

独立校验：

```bash
guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <same-commit> \
  --verify
```

`dist/SHA256SUMS.json` 会记录：

```text
Package Name 与 Version
Git Commit
Python Implementation / Version 与 Build Platform
Wheel 与 sdist 的文件名、Size、SHA-256
Wheel METADATA 与 sdist PKG-INFO 的 Name / Version 一致性
```

这里只声明 **Hash-only Provenance**。在没有真实签名系统时，GUIF 不会伪造 Cryptographic Signature、Trusted Builder Attestation 或第三方供应链认证。

## 一条命令完成初始化

初始化 Project、创建或验证 ChatGPT Host Credential，并打开私有 Conversation：

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

新 Conversation 首先进入 `theme-confirmation`。支持的 Theme 路径：

```text
theme-list       查看私有历史主题
theme-select     选择历史 Theme
theme-create     创建并绑定新 Theme
theme-derive     派生不可变的新 Theme Version
theme-unbound    明确本次不绑定 Theme
```

真实用户 Theme 内容只保存在 Framework Git 与 Project Git 之外的私有 Theme Library。公共示例和测试只使用完全虚构的 Fixture。

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

默认视图只显示 Conversation / Project、公开 Stage、提示信息、私有 Theme 摘要、上下文操作、安全的 Artifact 摘要和恢复状态。底层 Identity 与并发控制仍然严格执行。

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

GUIF 协调 Task-scoped Host Work Discovery、Task Etag、Exclusive Lease、绑定 Actor 的一次性 Claim、Immutable Attachment Retrieval、真实结果提交、Artifact Registration、确定性 Metadata Review、经过认证的 Semantic Review，以及下一用户阶段。

本地 Python Package 不会伪造 Pixel，也无法自行进入 ChatGPT 产品内部调用图片 Tool。ChatGPT 或其他配置 Host 必须嵌入 `ChatGPTHostLoop`，或消费 Authenticated Gateway Work API。Metadata Review 不能声称 Theme 一致性、构图、可读性或可用性已经通过；这些结论必须来自经过认证的 Semantic Visual Result。

## Controlled Revision

存在可执行视觉 Finding 时，会创建 Versioned Revision Job 和独立 Approval Gate。初始生成 Approval 不会自动授权修图。Source Artifact 会持续有效，直到 Replacement 是真实非模拟图片、Lineage 有效，并通过最终语义视觉检查。

## 已校验的私有备份

创建默认 Portable Backup：

```bash
guif-ready backup --workspace .
```

默认保存位置：

```text
<private-data-root>/backups/portable-<timestamp>.guif-private.zip
```

Portable Profile 包含可恢复的用户生产数据，例如 Theme、Conversation Binding / Record、Run、Plan、Host Work、Migration 和 Privacy Report。它明确排除 Host Credential Verifier、Operation Ledger Signing Key、Gateway Request Receipt 和 Operation Audit 中的认证材料。

`full-local` Archive 必须显式确认包含敏感材料：

```bash
guif-ready backup \
  --workspace . \
  --profile full-local \
  --include-sensitive \
  --output /protected/offline/location/full-local.guif-private.zip
```

未保护的 GUIF Archive 提供完整性校验，但不提供静态加密。

```bash
guif-ready backup-verify /path/to/portable.guif-private.zip
guif-ready backup-restore /path/to/portable.guif-private.zip
```

Restore 默认只生成计划。显式使用 `--conflict replace --apply` 时，会先创建 Portable Pre-restore Backup，再原子写入每个文件，并在落盘后重新校验 SHA-256。

## 外部备份保护边界

GUIF 不实现自定义加密算法，也不内置某个特定加密程序。它通过 `shell=False` 的 argv 数组协调一个显式配置的外部程序。

```bash
export GUIF_BACKUP_PROTECTOR_ID='local-encryption-tool'
export GUIF_BACKUP_PROTECT_COMMAND_JSON='["/path/to/protect-tool","encrypt","--input","{input}","--output","{output}"]'
export GUIF_BACKUP_UNPROTECT_COMMAND_JSON='["/path/to/protect-tool","decrypt","--input","{input}","--output","{output}"]'
export GUIF_BACKUP_PROTECT_TIMEOUT_SECONDS='300'
```

外部程序应通过自己的安全机制读取 Key 或 Passphrase。不要把 Secret 直接写入 JSON argv 配置。

```bash
guif-ready backup-protect \
  /path/to/portable.guif-private.zip \
  /protected/location/portable.guif-private.zip.protected
guif-ready backup-protection-verify \
  /protected/location/portable.guif-private.zip.protected
guif-ready backup-unprotect \
  /protected/location/portable.guif-private.zip.protected \
  /recovery/location/portable.guif-private.zip
```

Protection Boundary 不使用 Shell、必须显式配置、不存在未保护静默回退、执行时间受限、拒绝覆盖 Destination / Receipt、通过 Temporary File 发布、绑定原始与保护后文件的 Size / SHA-256，并且不持久化 Command argv 或 Secret Environment Value。加密强度、Key Custody、Rotation 和 Disaster Recovery 仍由外部程序与操作方负责。

## 支持的 Alpha Upgrade Assurance

规划从 alpha.27 或 alpha.28 升级到当前 beta 实现：

```bash
guif-ready upgrade \
  --workspace . \
  --source-release 1.0.0-alpha.28
```

默认计划要求先存在 Portable Backup，并检查 Private Schema Compatibility。审阅后显式执行：

```bash
guif-ready upgrade \
  --workspace . \
  --source-release 1.0.0-alpha.28 \
  --apply \
  --actor local-owner
```

未知 Source Release、未知未来 Schema、Invalid JSON 和 Raw Secret-like Field 会 Fail Closed。完整 Migration Evidence 只保存在私有 Upgrade / Migration Report；公共结果不返回 Private Path。

## Fault Injection

Fault Injection 只用于测试与开发，默认关闭。通过环境变量启用时必须同时设置：

```bash
export GUIF_FAULT_POINTS='backup-protection.before-publish'
export GUIF_ALLOW_FAULT_INJECTION='1'
```

只设置 Fault Point 而没有明确 Allow Flag 会直接报错。生产环境应保持两个变量均未设置。

## Extended Non-mutating Soak Profiles

Profile 对应有界迭代次数：

```text
quick       10
standard    100
extended    1000
```

执行 Profile，并可单独写出 Machine-readable Report：

```bash
guif-ready soak \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001 \
  --profile standard \
  --max-p95-ms 1000 \
  --report reports/soak.json \
  --no-persist
```

`--iterations` 仍可作为显式自定义覆盖。可选 `--backup` 会加入重复 Archive Verification。报告包含 Total / Mean / P50 / P95 / Max Timing、脱敏错误、观察到的公开 Stage、Threshold 状态、`production_state_mutated=false` 和 Failure Classification。性能 Threshold 未通过代表当前 Host / Environment Evidence 需要调查，不能单独证明 GUIF 产品正确性失败。

## Diagnostics 与 Acceptance

```bash
guif-ready diagnose \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
guif-ready acceptance \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

只有不存在 Blocking Readiness Check，并且 Conversation 为 `ready-to-export` 或 `completed` 时，Acceptance 才会通过。`--require-completed` 会要求最终 Gated Export 已成功。

## Compatibility 与 Support

```bash
guif-ready contract
guif-ready support
```

Compatibility Contract 保持：

```text
release: 1.0.0-alpha.28
origin_release: 1.0.0-alpha.28
current_release: 1.0.0-beta.2
channel: beta
public_api_version: 1
```

`release` 与 `origin_release` 标识 alpha.28 的冻结起点。Breaking Change 必须增加 Public API Version，并提供显式 Migration Path。Legacy `ProviderAdapter` 继续作为显式兼容路径。生产 Tool Routing 默认 ChatGPT-first，但 Host 与 Tool 均可替换；`dry-run` 只用于测试和开发，绝不作为生产静默回退。

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
  upgrade-reports/
  hardening-reports/
  runs/
  plans/
  migrations/
  privacy-reports/
```

真实 Theme、Prompt、Conversation Decision、Approval Evidence、Runtime State、Work Claim、Attachment、Image File、Semantic Finding、Credential、Backup / Protected Archive 与 Report 默认都保存在 Framework Git 和 Project Git 之外。

## 开发

```bash
pytest -q -W error::DeprecationWarning:PIL
python -m build
guif-ready provenance --dist dist --git-commit <commit>
guif-ready provenance --dist dist --git-commit <commit> --verify
```

## 当前限制

- ChatGPT 产品集成必须嵌入 `ChatGPTHostLoop` 或消费 Gateway Work API；本仓库不能自行调用 ChatGPT 内部图片 Tool。
- GUIF 可以校验外部保护 Evidence，但不能判断加密强度，也不能恢复丢失的 Key。
- Hash Provenance 不能替代真实签名或 Trusted Build Attestation。
- File-backed Work Claim 与 Task Lease 是单节点协调，不是分布式一致性系统。
- 内置 WSGI Gateway 不是 Internet-edge Reverse Proxy。
- 尚未实现 Remote Private-data Sync、Retention Automation 和 Multi-device Conflict Resolution。
- Current-tree Privacy Audit 不能证明历史 Commit、Fork、Cache 或外部 Clone 已清除。
