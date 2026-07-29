# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT；图片生成、修图、视觉检查、Git Operation 和 Export 都是可替换的 Tool 能力。

## 当前状态

`v1.0.0-alpha.21` 新增了可审阅、可持久化的 Host / Tool Discovery 与 Connection Workflow。

GUIF 现在明确区分：

```text
registered   当前 Runtime 已注册 Adapter
available    当前 Host 或本地 Runtime 现在可以使用
installable  Catalog 中存在，但尚未注册 Adapter
```

遇到 Tool 缺失时仍然 Fail Closed。对于符合条件的 `waiting-for-tool` 状态，Runtime 会关联一份 Connection Request，而不会静默安装 Plugin、明文索取 Secret，或者自动退回 `dry-run`。

alpha.20 的受控修图闭环保持不变：Revision Plan 转换为独立审批的 Edit Job；Source Artifact 不可变并进行 SHA-256 校验；Replacement 只有通过 Semantic Visual Review 后才能替代 Source。

## 产品规格

中英文双语持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。Feature、Test、CI、中英文 README、Version Metadata 和产品规格必须保持一致，Release 才算完成。

## Host Discovery

```python
runtime = Runtime(workspace)
report = runtime.discover_host()
```

报告使用 `guif-host-capability-discovery-v1`，包括：

- Host Identity；
- Host 声明的 Capability；
- 当前 Available Tool ID；
- Host Metadata；
- Discovery Timestamp。

默认 ChatGPT Host 会声明 `chatgpt-image`、图片生成、图片编辑、Protected Region Editing、透明输出、视觉检查和 Git Operation 能力。

## Tool Discovery

```python
tools = runtime.discover_tools(project="LeekParty")
```

每个 Tool Discovery Record 包含：

- `status` 与完整 `states`；
- Registered、Available、Installable、Ready 状态；
- Tool Manifest 或 Catalog Metadata；
- Host 与 Execution Mode；
- 当前 Health Check；
- Project 最新 Connection Status；
- Permission、Data Scope、External Call、Cost、Credential 和 Host Support Disclosure。

Workspace 可在以下文件声明 Installable Tool：

```text
.guif/tool-catalog.json
```

示例：

```json
{
  "tools": [
    {
      "tool_id": "custom-image",
      "name": "Custom Image Tool",
      "version": "1.0",
      "capabilities": ["image-generation", "image-editing"],
      "install_method": "plugin-manager",
      "source": "trusted-workspace-catalog",
      "permissions": ["network-access"],
      "data_scopes": ["prompt-job", "approved-reference-images"],
      "external_call": true,
      "billable": true,
      "requires_credentials": true,
      "credential_kind": "api-key-reference"
    }
  ]
}
```

Catalog Entry 只代表“可以安装”，不会自动安装或注册 Tool。

## Connection Workflow

```text
Tool 缺失或不可用
  -> Connection Request
  -> 审阅 Disclosure
  -> Approve 或 Reject
  -> installation-required / waiting-for-credentials / waiting-for-host-support
  -> Health Check Retry
  -> connected
  -> 继续执行同一个 Persisted Job
```

创建并批准连接：

```python
request = runtime.request_tool_connection(
    "LeekParty",
    "image-generation",
    "chatgpt-image",
    requested_by="ChatGPT Host",
)

connected = runtime.approve_tool_connection(
    "LeekParty",
    request["request_id"],
    actor="project-owner@example.com",
    comment="已审阅权限和数据范围。",
)
```

Reject 不会修改 Project Tool Configuration。

批准一个只有 Installable 状态的 Tool，会得到 `installation-required`；GUIF 不会自动安装。需要 Credential 的 Tool 在没有 Credential Reference 时会保持 `waiting-for-credentials`。

## Credential Policy

GUIF Connection State 只保存引用，例如：

```text
env://CUSTOM_IMAGE_API_KEY
secret-manager://projects/leek-party/custom-image
```

不会保存 Credential Secret 本身：

```json
{
  "credential": {
    "required": true,
    "kind": "api-key-reference",
    "reference": "env://CUSTOM_IMAGE_API_KEY",
    "secret_stored_by_guif": false
  }
}
```

Credential 解析和 Secret 保存由 Host、Plugin、运行环境或 Secret Manager 负责。

## Health Retry

```python
retry = runtime.retry_tool_health("LeekParty", "chatgpt-image")
```

Health Retry 会追加写入 `tool-connections.json`。已经 Approved 的 Request 在 Host、Tool 或 Credential 配置恢复健康后，可以转换为 `connected`。

## Tool Adapter Contract Test

```python
report = runtime.run_tool_contract_tests("chatgpt-image")
```

Runner 不会进行外部调用，检查：

- Manifest Schema 与 Identity；
- Capability Declaration；
- Input / Output Contract；
- Execution Mode 对应的 `prepare()` 或 `execute()` 实现；
- Permission、Data Scope、Cost 和 Credential Disclosure；
- Health Check Identity 与 Status Shape。

Adapter Scaffold 现在会提示开发者补齐 Disclosure，并运行：

```bash
guif tool-contract-test <tool-id>
```

Contract Test Passed 不代表 Plugin 已安装、可信、签名或自动注册。

## 默认 ChatGPT 路径

```text
用户
  -> ChatGPT Host
  -> GUIF Runtime
  -> Approval
  -> Tool Resolver
  -> chatgpt-image
  -> External Handoff
  -> ChatGPT 生成图片或修图
  -> Host 提交真实文件
  -> Artifact Registry
  -> Visual Review / Controlled Revision
  -> Gated Export
```

ChatGPT Host 与 `chatgpt-image` 是默认值，不是 GUIF Core 的硬编码依赖。`dry-run` 仍然只能显式用于 Contract Test，绝不会成为生产环境的隐式回退。

## CLI

```bash
guif host-discover

guif tool-discover --project LeekParty

guif tool-connect-request image-generation chatgpt-image \
  --project LeekParty \
  --requested-by "ChatGPT Host"

guif tool-connect-list --project LeekParty

guif tool-connect-approve <request-id> \
  --project LeekParty \
  --actor project-owner@example.com

guif tool-connect-reject <request-id> \
  --project LeekParty \
  --actor project-owner@example.com

guif tool-health-retry chatgpt-image --project LeekParty

guif tool-contract-test chatgpt-image
```

原有的 `run-execute`、`run-tool-submit`、`run-revision-create`、`run-revision-approve`、`run-revision-execute` 和 `run-artifact-review` 等生产命令继续保留。

## 持久化

Project 级 Tool Discovery 和 Connection Evidence 保存于：

```text
projects/<project>/tool-connections.json
```

其中包括 Connection Request、Decision、Disclosure Snapshot、Credential Reference、Status Transition 和 Health Check History。Task 级 Tool Resolution 与 Handoff 仍保存在对应 Run Directory 中。

## 当前限制

- GUIF 尚不会自动安装 Plugin，也不会动态加载新安装的 Adapter。
- Host 和 Approval Actor 仍未经过身份认证。
- GUIF Core 不负责解析 Credential Reference。
- Workspace Catalog 尚无签名和远程可信校验。
- ChatGPT 产品侧自动消费 Handoff 并回传结果的 Wiring 仍在 GUIF Core 之外。
- 默认 Semantic Visual Inspector Registry 仍为空。
- 内置 Export Agent 仍为 Contract-only。

## 运行原则

1. Discovery 是证据，不等于安装。
2. Connection 必须显式审批。
3. 连接前必须披露 Permission、Data Scope、External Call、Cost 和 Credential。
4. GUIF 只保存 Credential Reference，不保存 Secret。
5. 生产 Tool 异常必须 Fail Closed。
6. Contract Test 不得执行外部调用。
7. ChatGPT 是默认 Host 和图片 Tool，不是硬编码依赖。
8. Revision Source 保持不可变，Replacement 必须通过 Review 后才能 Supersede。

## 下一阶段

下一优先级是 **alpha.22：Gated Export Agent**。Export Agent 将消费 Active Artifact、Contract QA、Visual Review、Revision Resolution 和 Project Resource Contract，再把 Approved Production Asset Materialize 到 Project Truth 和对应 Engine Export Output。
