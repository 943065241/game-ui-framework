# GUIF Product Specification / GUIF 产品规格说明

> Status / 状态: Living document / 持续迭代文档  
> Baseline / 基线版本: `v1.0.0-alpha.23`  
> Last reviewed / 最近审阅: 2026-07-29

---

## 中文版

### 0. 文档目的

本文件定义 GUIF 的产品定位、已验证能力、隐私边界、风险和下一阶段。Feature、Test、CI、中英文 README、Version Metadata 和本文件必须在同一个 Release 中保持一致。

### 1. 产品定义

GUIF 是一个本地优先、以自然语言为主要入口、Host 与 Tool 均可配置、面向游戏 UI 全生产流程的可执行 AI 工作框架。

默认路径：

```text
用户
  -> ChatGPT Host                         默认，可替换
  -> Conversation Theme Resolution
       -> 选择历史 Theme
       -> 创建新 Theme
       -> 派生 Theme Version
       -> 明确暂不绑定
  -> GUIF Runtime
       -> Planner / Director / Theme / Resource / Prompt
       -> Approval
       -> Tool Discovery / Connection / Execution
       -> Artifact Registry
       -> Visual Review
       -> Controlled Revision
       -> Gated Export
       -> Project Truth / Engine Output / Audit
```

核心原则：

1. Theme 是用户拥有的私有长期数据，不属于框架工程；
2. 新对话先确认 Theme，再开始依赖视觉方向的生产；
3. Theme 通过对话维护，每次发布形成不可变 Version；
4. 框架 Git 只保存 Contract、代码、测试和完全虚构的示例；
5. Project Git 默认不保存 Theme 内容，只保存明确批准的生产事实；
6. Runtime 持久化只保存 Theme ID、Version 和 Snapshot Hash；
7. 真实 Theme 只在执行时从私有存储 Hydrate；
8. 缺少 Theme 时 Fail Closed，不静默套用框架内置风格；
9. 删除当前文件不等于删除 Git 历史；历史清理必须单独评估；
10. Approval、Visual Review、Artifact Identity 与 Gated Export 规则保持不变。

### 2. alpha.23 已验证能力

#### 2.1 Private Theme Library

`PrivateThemeStore` 将 Theme 保存到 Workspace 仓库之外：

```text
<private-data-root>/themes/<theme-id>/
  index.json
  versions/1.json
  versions/2.json
```

可通过 `GUIF_DATA_HOME` 指定私有数据父目录。未配置时使用 Workspace 外部的隐藏同级目录。

Theme Record 包含：

- `theme_id`；
- `version` 与 `parent_version`；
- `name`、`status`、`privacy`；
- Theme Content；
- Conversation / Host 来源记录；
- `snapshot_hash`；
- 创建与更新时间。

Theme Content 包含：

```text
description
palette
materials
lighting
must_include
avoid
```

每个 Version 都是不可变 Snapshot。`derive()` 创建新 Version，不覆盖旧版本。

#### 2.2 Conversation-first Resolution

新对话调用：

```python
runtime.prepare_conversation_theme(
    conversation_id,
    project="SampleGame",
)
```

状态：

```text
selected
confirmation-required
```

`confirmation-required` 提供：

```text
select-history
create-theme
derive-theme
continue-unbound
```

当 `Runtime.run()` 收到 `conversation_id` 且对话尚未绑定 Theme 时，默认抛出 `ThemeResolutionRequired`。只有 Host 完成选择，或明确设置 `continue_unbound=True`，Task 才继续。

#### 2.3 Theme Binding

Conversation 与 Project Binding 均存放在私有目录：

```text
conversation-theme-bindings/<conversation-id>.json
project-theme-bindings/<project>.json
```

解析优先级：

```text
Conversation Binding
  -> Project Binding
  -> Unbound
```

Binding 只保存：

```json
{
  "theme_id": "theme-example",
  "version": 2,
  "snapshot_hash": "sha256...",
  "privacy": "private"
}
```

#### 2.4 Runtime Context Redaction

执行中的 `RuntimeContext.active_theme` 可以包含完整 Theme，供 Planner、Director、Theme、Prompt 和 QA 使用。

持久化时：

```text
active_theme = null
active_theme_ref = opaque reference
```

Task 重新加载时，TaskStore 根据 ID、Version 与 Hash 从 PrivateThemeStore 重新 Hydrate。Hash 不一致时 Fail Closed。

#### 2.5 Private Runtime Evidence

新的 Task Run 与自然语言 Plan 均存放在私有目录：

```text
<private-data-root>/runs/<project>/<task-id>/
<private-data-root>/plans/<project>/
```

原因：Task、Prompt IR、Theme Contract、Review Finding、Revision Plan 和用户决策可能包含私人内容。

旧版 `projects/<project>/runs/` 暂时保持只读兼容，所有新写入均使用私有路径。

#### 2.6 Explicit Theme Requirement

GUIF 不再内置可能与真实用户项目相似的 Theme Preset，也不会仅根据 Task 文本静默推断完整 Theme。

缺少明确选择的 Theme 时：

```text
Theme Contract.status = blocked
source = unresolved
approval_required = true
```

Theme Agent 的来源现在是：

```text
private-theme
unresolved
```

#### 2.7 Legacy Migration

```python
runtime.migrate_legacy_project_themes(
    "SampleGame",
    actor="migration",
)
```

迁移步骤：

1. 读取旧 `projects/<project>/themes/*.json`；
2. 导入 PrivateThemeStore；
3. 在私有 Migration 目录保存 Archive 与 Report；
4. 删除 Project-local Theme 文件；
5. 删除 `project.json` 中的 `current_theme` 与 `theme_binding`；
6. 将旧 Active Theme 转换成私有 Project Binding。

#### 2.8 Privacy Audit

```python
runtime.audit_privacy(
    sensitive_terms=("private phrase",),
)
```

Working-tree Audit 检查：

- Project-local Theme 文件；
- Project-local Run、Context、Output 与 Plan；
- Project Config Theme Binding；
- 私有 Theme Snapshot 命名；
- 调用方提供的敏感词。

Report 保存在私有目录。该 Audit 只覆盖当前 Working Tree，不覆盖历史 Commit、PR Diff、Fork、缓存、Release 或外部 Clone。

#### 2.9 Repository Guard

`.gitignore` 阻止常见私有数据路径进入 Git。CI 还包含 Repository Privacy Test，防止已知用户 Theme Identifier 再次进入当前框架树。

所有框架测试均使用完全虚构的 `SampleGame` 与抽象几何 Fixture。

### 3. 与既有能力的关系

alpha.23 保留并继续使用：

- Workflow-driven Agent Pipeline；
- Initial Approval 与 Revision Approval；
- Configurable Host / Tool 与 ChatGPT Handoff；
- Artifact Registry 与 SHA-256 Identity；
- Metadata / Semantic Visual Review；
- Controlled Revision 与 Review-gated Supersession；
- Gated Export、Engine Manifest、Transaction Audit 与 Conflict-aware Rollback。

区别是这些 Runtime Evidence 现在默认位于 Private Data Store。

### 4. 隐私边界

#### 4.1 可以进入框架 Git

- 数据结构与接口；
- 通用算法；
- 完全虚构、无法关联真实用户项目的 Fixture；
- 不包含真实 Theme 内容的文档示例；
- Privacy 与 Migration 工具本身。

#### 4.2 不得进入框架 Git

- 真实 Theme 名称与描述；
- 用户配色、材质、角色、场景和构图规范；
- 对话中的 Theme 决策与迭代；
- 用户 Artifact、Prompt、Review Finding；
- 私有 Theme Binding；
- 含私人内容的 Task Run 与 Plan。

#### 4.3 Project Git

Project Git 只保存用户明确批准成为项目事实的数据，例如生产 Resource 与 Workflow。Theme 默认只通过私有引用解析，不复制完整内容。

### 5. Git 历史事件响应

当前分支清理不能撤回已经存在于：

```text
prior commits
pull-request diffs
forks
caches
release archives
external clones
```

GUIF 不自动重写历史，因为 History Rewrite 是破坏性操作，可能影响 Clone、Fork、Open PR、Tag 与 Release。

处理流程：

1. 停止继续提交私人内容；
2. 清理当前树并加入 CI Guard；
3. 确定准确文件、Commit、PR、Tag 和 Release 范围；
4. 备份 Repository；
5. 决定是否需要 `git filter-repo` 等历史重写；
6. 协调 Force Push、Tag/Release 替换和协作者重新 Clone；
7. 申请清理平台缓存；
8. 承认 Fork 和外部 Clone 无法保证收回。

详细步骤见 `docs/PRIVACY_MIGRATION.md`。

### 6. 当前边界

- Private Data Store 为本地文件系统，尚无静态加密；
- 没有跨设备私有 Theme 同步；
- 没有 Retention Policy、Lease 或并发编辑锁；
- Conversation / Approval Actor 尚未认证；
- ChatGPT 产品侧自动 Handoff Callback 尚未接入；
- 默认 Semantic Visual Inspector Registry 为空；
- 当前 Tree Audit 无法证明历史或外部副本已清理；
- Memory 仍属于 Project 数据，Theme 设计决策应写入 Theme Version 而非普通 Project Memory。

### 7. 下一阶段

#### alpha.24：Authenticated Host API 与 Git Change Management

- Authenticated Host / Approval / Export Actor；
- Stable Host Result Callback；
- Optimistic Concurrency 与 Task Lease；
- Git Change Set；
- Branch、Commit、Diff 与 Revert；
- Export Transaction 与 Git Commit 关联；
- Pause、Cancel、Timeout 与 Result Summary。

### 8. 迭代记录

- `alpha.16`：Persistent Approval；
- `alpha.17`：Provider Adapter 与 Artifact Registry；
- `alpha.18`：Visual Review 与 Revision Plan；
- `alpha.19`：Configurable Host / Tool 与 ChatGPT Handoff；
- `alpha.20`：Controlled Revision Execution；
- `alpha.21`：Tool Discovery 与 Connection Workflow；
- `alpha.22`：Gated Export 与 Transaction Rollback；
- `alpha.23`：Private Theme Library、Conversation Theme Resolution、Runtime Redaction 与 Privacy Migration。

---

## English Version

### 0. Purpose

This file defines GUIF's product direction, verified capabilities, privacy boundary, risks, and next phase. Features, tests, CI, both READMEs, version metadata, and this specification must agree in the same release.

### 1. Product definition

GUIF is a local-first executable AI work framework for end-to-end game UI production. Hosts and Tools are configurable; ChatGPT remains the default Host.

A Theme is private, user-owned, versioned long-term data. It does not belong to the framework repository. A new conversation resolves a Theme before visual production by selecting history, creating a Theme, deriving a version, or explicitly continuing unbound.

### 2. Verified alpha.23 capabilities

- Versioned `PrivateThemeStore` outside workspace Git;
- immutable Theme snapshots with parent versions and SHA-256 identity;
- private Conversation and Project bindings;
- conversation-first `confirmation-required` resolution;
- `ThemeResolutionRequired` before an unbound conversation Task starts;
- transient full Theme hydration and persisted opaque references only;
- private Task Run and natural-language Plan storage;
- explicit Theme requirement with no silent embedded preset inference;
- legacy project Theme migration;
- current-working-tree privacy audit and repository CI guard;
- fictional, non-user-linked framework examples.

### 3. Private data boundary

Framework Git may contain contracts, algorithms, interfaces, privacy tooling, and wholly fictional fixtures. It must not contain real Theme names, visual direction, palette, materials, character or scene rules, conversation decisions, user Artifacts, Prompt data, review findings, or private bindings.

Project Git stores approved production truth. Complete Theme data remains private by default.

### 4. History boundary

Deleting current files does not erase prior commits, PR diffs, forks, caches, releases, or external clones. GUIF does not automatically rewrite Git history. A destructive rewrite requires a scoped incident response, backup, collaborator coordination, force-push plan, tag/release replacement, and cache cleanup request.

### 5. Current limitations

Private storage is file-backed and lacks encryption-at-rest, cross-device synchronization, retention policies, and concurrent leases. Actors are not authenticated. Current-tree audit cannot prove removal from repository history or external copies.

### 6. Next phase

**alpha.24: Authenticated Host API and Git Change Management** will add authenticated actors, stable result callbacks, optimistic concurrency, Task leases, Git change sets, branch/commit/diff/revert integration, and Export transaction linkage.
