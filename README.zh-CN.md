# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、Host 与 Tool 均可配置的游戏 UI 生产框架。默认 Host 是 ChatGPT，默认图片生成与修图 Tool 是 `chatgpt-image`，但二者都不是 GUIF Core 的硬编码依赖。

## 当前状态

`v1.0.0-alpha.23` 将用户 Theme 数据与框架 Git、项目 Git 分离。

Theme 现在属于用户拥有的私有、可版本化长期数据。公开框架仓库只保存 Contract、存储接口、工作流代码、测试，以及完全虚构的 Fixture；真实 Theme 名称、视觉规则、配色、材质、对话决策和迭代历史均存放在仓库之外。

```text
开始新对话
  -> 先确认 Theme
       -> 从历史 Theme 中选择
       -> 新建 Theme
       -> 从旧版本派生新版本
       -> 明确选择暂不绑定
  -> 绑定 Theme ID + Version + Snapshot Hash
  -> 开始规划与生产
  -> 在对话中继续完善 Theme
  -> 发布新的不可变 Theme Version
```

中英文双语产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。隐私迁移和 Git 历史处理指引见 [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md)。

## 私有数据目录

可通过 `GUIF_DATA_HOME` 指定私有数据父目录。未配置时，GUIF 使用 Workspace 仓库外部的隐藏同级目录。

```text
<private-data-root>/
  themes/<theme-id>/
    index.json
    versions/1.json
    versions/2.json
  conversation-theme-bindings/<conversation-id>.json
  project-theme-bindings/<project>.json
  runs/<project>/<task-id>/
  plans/<project>/
  migrations/
  privacy-reports/
```

Project Git 不保存完整 Theme 内容。持久化 Task Context 只保存不透明引用：

```json
{
  "active_theme_ref": {
    "theme_id": "theme-example",
    "version": 2,
    "snapshot_hash": "sha256...",
    "privacy": "private"
  }
}
```

Runtime 执行时才会在经过批准的私有数据边界内加载完整 Theme。

## 对话优先的 Theme Resolution

```python
from pathlib import Path
from guif.runtime import Runtime, ThemeResolutionRequired

runtime = Runtime(Path.cwd())
resolution = runtime.prepare_conversation_theme(
    "conversation-001",
    project="SampleGame",
)
```

新对话尚未绑定 Theme 时会返回 `confirmation-required`。视觉生产不会再根据任务文本静默套用框架内置风格。Host 必须让用户选择历史 Theme、新建 Theme、派生版本，或者明确选择暂不绑定。

创建并绑定一个完全虚构的示例 Theme：

```python
record = runtime.create_private_theme(
    "Geometric Arcade",
    {
        "description": "抽象几何形状和中性测试表面。",
        "palette": ["test blue", "test gray"],
        "materials": ["matte polymer"],
        "lighting": "flat studio light",
        "must_include": ["hexagonal navigation"],
        "avoid": ["real brands"],
    },
    actor="host",
    conversation_id="conversation-001",
    project="SampleGame",
)
```

根据对话反馈派生不可变新版本：

```python
revision = runtime.derive_private_theme(
    record["theme_id"],
    {"lighting": "soft top light"},
    from_version=1,
    actor="host",
    conversation_id="conversation-001",
)
```

Version 1 保持不变，对话绑定移动到经过确认的新版本。

## 私有 Runtime Evidence

Task Run 和自然语言 Plan 也可能包含 Prompt、Theme Contract、Review Finding 与用户决策，因此同样迁移到私有数据存储。

```text
公开 Project Tree
  project.json
  workflows/
  production-assets/          仅存已批准生产事实
  memory/                     用户明确选择由项目管理的记录

私有数据目录
  themes/
  runs/
  plans/
  conversation bindings/
```

旧版 Project-local Run 暂时保持只读兼容，所有新 Run 只写入私有目录。

## 迁移与隐私审计

```python
report = runtime.migrate_legacy_project_themes(
    "SampleGame",
    actor="migration",
)

audit = runtime.audit_privacy(
    sensitive_terms=("private phrase",),
)
```

迁移会将旧 Theme 文件导入私有库，删除 Project-local Theme 文件和绑定，并在私有目录中生成 Migration Report。Working-tree Audit 会检查常见私有数据路径，也可以检查调用方提供的敏感词。

从当前分支删除文件，**不等于**删除历史 Commit、PR Diff、Fork、缓存、Release Archive 或外部 Clone。GUIF 不会自动执行破坏性的历史重写。应先确定准确暴露范围，再按照隐私迁移文档执行仓库事故响应。

## 既有生产流程

```text
私有 Theme 选择
  -> Planner / Director / Theme / Resource / Prompt
  -> Approval
  -> 配置的图片 Tool 或 ChatGPT Handoff
  -> Artifact Registry
  -> Metadata 与 Semantic Visual Review
  -> Controlled Revision
  -> Gated Export
  -> Project Truth / Engine Output / Audit / Rollback
```

Gated Export 仍要求 Task 完成、Contract 已审批、Visual Review 通过、Artifact SHA-256 有效、Revision 已解决且 Engine 兼容，才允许写入生产文件。

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

- ChatGPT 产品侧仍需要自动消费 External Handoff 并提交文件；
- 默认 Semantic Visual Inspector Registry 仍为空；
- 私有存储目前基于文件，尚未提供静态加密、远程同步、Retention Policy 或并发 Lease；
- Conversation、Approval 与 Export Actor 仍是字符串，不是认证身份；
- 当前 Working-tree Audit 无法证明 Git 历史、Fork、缓存或外部 Clone 已被清理；
- Git Change Set、Signed Manifest 与 Authenticated Host Callback 尚未完成。

## 下一阶段

下一优先级是 **alpha.24：Authenticated Host API 与 Git Change Management**，包括 Authenticated Actor、Optimistic Concurrency、Task Lease、Stable Host Result Callback、Git Change Set、Branch、Commit、Diff、Revert，以及 Export Transaction 与 Git Commit 的关联。
