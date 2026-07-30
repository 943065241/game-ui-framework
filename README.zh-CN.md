# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

> **构建受治理的 AI 生产系统，而不仅仅是 Prompt。**

GUIF 是一个本地优先的 AI 生产工作流与治理框架。它当前首先实现并服务于**游戏 UI 生产**，但其工作流模型——生产任务、审批、产物、能力路由、候选试验、正式采用、回归与恢复——面向更广泛的 AI 生产系统设计。

ChatGPT / Codex 是默认 **Host**，`chatgpt-image` 是默认图片生成与修图 **Tool**，`chatgpt-vision` 是默认语义视觉检查器。它们都是可替换契约，而不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-beta.3` 已把 Candidate Change 与 Tool Trial 纳入正式生产闭环。

- Python 3.10、3.11、3.12 全部通过完整 CI。
- CI 包含构建、Hash Provenance、Wheel 安装和 CLI Contract 检查。
- 177 个测试通过。
- Production Task 与框架 Improvement Case 是两个独立对象。
- 批准候选试验不等于批准采用、合并、发布或替换稳定 Tool 路由。
- 没有真实候选产物和真实语义视觉证据，候选不能进入正式采用。

Codex Plugin Version 为 `1.0.0-beta.3`。Python Package 仍为 `1.0.0b2`；Public API 兼容性继续由项目 Compatibility Contract 管理。

重要文档：

- [持续迭代产品规格](docs/GUIF_PRODUCT_SPEC.md)
- [Support Policy](SUPPORT.md)
- [Privacy Migration Guidance](docs/PRIVACY_MIGRATION.md)

## GUIF 是什么

GUIF 协调两个相互连接、但彼此隔离的闭环。

### 1. AI 生产闭环

```text
Theme / 生产上下文
  -> 自然语言需求
  -> 生产计划
  -> 上下文审批
  -> 真实生成或修图
  -> 确定性 Metadata Review
  -> 语义视觉检查
  -> 必要时单独审批 Revision
  -> Gated Export
```

### 2. 持续改进闭环

```text
生产中发现问题
  -> 保存检查点并暂停 Production Task
  -> 创建私有 Improvement Case
  -> 诊断真正原因
  -> 提出候选改进方案
  -> 用户批准隔离试验
  -> 构建或运行候选版本
  -> 生成真实候选结果
  -> 用户审核稳定版与候选证据
  -> 用户采用、继续调整或放弃候选
  -> 发布代码或应用指定范围的 Tool 路由
  -> 刷新 Host 插件
  -> 正式回归
  -> 恢复原 Production Task
```

生产任务不会变成代码开发任务。Improvement Case、候选证据和开发交接包默认保存在私有目录，不进入 Project Git。

## 设计原则

### 生产与演进隔离

GUIF 在独立环境中调查和试验候选方案，同时保留稳定生产状态。

### 试验审批与采用审批分离

试验审批只允许隔离实验，不允许 GUIF 合并代码、发布插件、覆盖稳定 Skill 或修改稳定 Tool 路由。

### 必须有真实证据

Dry Run、伪造图片、模拟语义结论或计划中的 Tool 调用，都不能被当作成功的生产结果。正式采用必须建立在真实候选产物和真实语义视觉检查之上。

### 先诊断，再归类

反复出现的视觉缺陷不会被自动归类为 Skill 缺陷。GUIF 可以同时检查 Skill 约束、Prompt IR、编辑范围、Theme 规则、连续修图损伤、检查覆盖率和 Tool 固有表现。

### 按能力路由，而不是按品牌整体替换

Tool 只替换匹配的能力。例如，Figma 可以负责可编辑的结构化布局，但不会因此自动替代插画生成、像素级修图、语义视觉检查或 Unity 导出。

### 正式采用必须声明范围

Tool 候选可以采用到：

- 当前 Task；
- 当前 Project；
- 整个 Workspace。

隔离试验期间，稳定的 Project 与 Workspace 路由保持不变。

## 系统架构

```text
用户
  |
  v
Host：ChatGPT / Codex
  - 理解用户意图
  - 驱动 GUIF 工作流
  - 调用图片与视觉 Tool
  - 修改候选代码或 Skill
  - 执行测试、Git、CI 与发布操作
  |
  v
GUIF Core
  - Production Task
  - Conversation Workflow
  - Approval Gate
  - Artifact 与 Lineage
  - Improvement Case
  - Candidate Change
  - Tool Trial
  - Regression、Checkpoint 与 Recovery
  |
  v
Tools / Adapters
  - GPT Image 生成与修图
  - 语义视觉检查
  - 结构化布局 Tool
  - 游戏引擎导出 Adapter
  - 其他按能力划分的集成
```

Host 是主动执行者，GUIF Core 是工作流与治理权威，Tool 提供具体生产能力。

## 模拟使用例：游戏 UI 生产与 GUIF 改进

下面的对话用于说明预期用户体验。它是工作流模拟，不代表其中出现的每个外部 Tool 都已经完成集成。

### 开始生产

**用户**

> 使用 GUIF 创建一个 1920x1080 的科幻背包界面，沿用当前 Project Theme。先提交计划，未经批准不要生成。

**GUIF Host**

> Production Task 已创建，Theme 已确认。计划包含角色装备区、物品网格、详情面板和 Unity 导出。等待生产审批。

**用户**

> 批准生产。

**GUIF Host**

> GPT Image 已生成真实候选图片。Metadata Review 通过。语义视觉检查认为布局可用，但编辑后的详情面板存在明显噪点。

### 进入 Candidate Change

**用户**

> 这次修图又引入了明显噪点，这是 GUIF 问题，进入 Candidate Change 迭代流程。

**GUIF Host**

> Production Task 已暂停并保存检查点，私有 Improvement Case 已创建。
>
> 本次诊断将比较：
> - Skill 中的修图约束；
> - Prompt IR 与编辑范围；
> - Theme 的清洁度要求；
> - 连续修图造成的累积损伤；
> - 语义视觉检查覆盖率；
> - 当前图片 Tool 的固有表现。

**GUIF Host**

> Candidate A 缩小可编辑区域，并增加明确的表面清洁度约束。Candidate B 保持稳定 Skill 不变，试验另一条编辑路由。批准试验不会修改稳定 Skill 或 Tool 路由。

**用户**

> 批准 Candidate A 试验。

### 审核真实候选证据

**GUIF Host**

> Candidate A 已在隔离环境执行，生成了真实图片，并完成语义视觉检查。
>
> 稳定版：详情面板存在可见颗粒。
>
> Candidate A：面板更干净，字体保持正常，没有新增阻断问题。
>
> 请选择：正式采用、继续调整候选版本，或放弃候选并保留稳定版本。

**用户**

> 正式采用 Candidate A。

**GUIF Host**

> 已批准采用。候选改动现在可以进入开发与发布路径。CI 已通过，插件已刷新，正式回归通过，原 Production Task 已从检查点恢复。

### 试用不同 Tool

**用户**

> 当前 Tool 不适合结构化 UI 布局，试用 Figma，只负责布局，采用范围为当前 Project。

**GUIF Host**

> GUIF 会先检查注册状态、可用性、Host 支持、权限、外部数据流、收费与凭证。
>
> 如果 Figma 可用，GUIF 会创建隔离 Candidate Task，并仅把结构化布局能力路由到 Figma。如果尚未集成，GUIF 会创建 `tool-integration-change` 候选，而不会假装调用成功。

这个例子体现了 GUIF 的核心规则：**只有隔离候选产生真实证据，并由用户明确正式采用，稳定生产系统才允许发生变化。**

## 安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

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

## Conversation-first 生产

新 Conversation 首先进入 `theme-confirmation`。支持的 Theme 路径包括：

```text
theme-list       查看私有历史 Theme
theme-select     选择已有 Theme
theme-create     创建并绑定新 Theme
theme-derive     派生不可变的新 Theme Version
theme-unbound    明确本次不绑定 Theme
```

提交自然语言需求：

```bash
guif-conversation submit \
  --project SampleGame \
  --conversation conversation-001 \
  --request-key chat-turn-001 \
  "创建一个虚构的 1080x2340 天文台商店页面并导出 Unity"
```

批准当前 Initial 或 Revision Gate：

```bash
guif-conversation approve \
  --project SampleGame \
  --conversation conversation-001
```

默认用户视图会隐藏 Approval ID、Task ID、Etag、Lease、Claim、Handoff ID 与 Callback ID 等底层标识，但 GUIF 仍会在内部严格执行这些约束。

## 真实图片与语义视觉闭环

由配置后的 Host 提供真实图片与视觉能力：

```python
view = conversation.run_host_until_blocked(
    "SampleGame",
    "conversation-001",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

本地 Python Package 不会伪造 Pixel，也无法自行进入 ChatGPT 产品内部 Tool Runtime。ChatGPT / Codex 或其他配置 Host 必须嵌入 Host Loop，或消费经过认证的 Gateway Work API。

Metadata Review 只验证确定性属性，不能声称 Theme 一致性、构图、可读性、噪点或可用性已经通过；这些结论必须来自经过认证的语义视觉结果。

## Controlled Revision

存在可执行视觉 Finding 时，会创建 Versioned Revision Job 和独立 Approval Gate。初始生成 Approval 不会自动授权修图。Source Artifact 会持续有效，直到 Replacement 是真实非模拟产物、Lineage 有效，并通过语义视觉检查。

## Tool Trial 与集成变更

Tool Trial 会检查：

- Tool 注册、可用性与健康状态；
- Host 兼容性；
- 权限与数据范围；
- 外部调用与收费；
- Credential 要求；
- Capability 是否匹配；
- 采用范围与回退方式。

未知或不可用的 Tool 会被转换为 `tool-integration-change` 候选，需要开发 Adapter、权限声明、健康检查、结果回传契约和 Contract Test。GUIF 不会把不可用 Tool 伪装成成功执行。

## Release Artifact Provenance

构建正式产物：

```bash
python -m build
```

生成并验证 SHA-256 Provenance Manifest：

```bash
guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <40-or-64-character-hex-commit>

guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <same-commit> \
  --verify
```

`dist/SHA256SUMS.json` 会把 Package Metadata 与产物 Hash 绑定到 Git Commit。这是 Hash-only Provenance，不是 Cryptographic Signature 或 Trusted Builder Attestation。

## 已校验的私有备份

```bash
guif-ready backup --workspace .
guif-ready backup-verify /path/to/portable.guif-private.zip
guif-ready backup-restore /path/to/portable.guif-private.zip
```

默认保存位置：

```text
<private-data-root>/backups/portable-<timestamp>.guif-private.zip
```

Restore 默认先生成计划。敏感本地材料需要显式选择 `full-local`。未保护 Archive 提供完整性验证，但不提供静态加密。

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
  improvement-cases/
  candidate-evidence/
  development-handoffs/
  backups/
  diagnostics/
  upgrade-reports/
  hardening-reports/
  runs/
  plans/
  migrations/
  privacy-reports/
```

真实 Theme、Prompt、Decision、Approval、Runtime State、图片、语义 Finding、Credential、Improvement Case、候选证据、Backup 与 Report 默认都保存在 Framework Git 和 Project Git 之外。

## 开发

```bash
pytest -q -W error::DeprecationWarning:PIL
python -m build
guif-ready provenance --dist dist --git-commit <commit>
guif-ready provenance --dist dist --git-commit <commit> --verify
```

## 当前边界

- GUIF 当前首先实现游戏 UI 生产；扩展到其他 AI 生产领域仍需要相应的 Domain Contract、Tool、Review Criteria 与 Export Adapter。
- ChatGPT / Codex 集成必须嵌入 Host Loop 或消费 Gateway Work API；Python Package 本身不能直接调用产品内部 Tool。
- 文件型 Work Claim 与 Task Lease 是单节点协调机制，不是分布式共识。
- Hash Provenance 不能替代 Release Signing 或 Trusted Build Attestation。
- GUIF 可以验证外部 Backup Protection Evidence，但无法判断其密码学强度，也不能恢复丢失的 Key。
- 内置 WSGI Gateway 不是 Internet-edge Reverse Proxy。
