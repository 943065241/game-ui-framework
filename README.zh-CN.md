# AIPG — AI 生产与治理框架

[English](README.md) | **简体中文**

> 构建受治理的 AI 生产系统，而不只是 Prompt。

AIPG 是一个本地优先的 AI 生产工作流与治理框架，负责路由、执行、检查、修订和导出 AI 生产任务。GUIF 保留为游戏 UI 与视觉生产领域。

ChatGPT / Codex 是默认 Host。图片生成、语义视觉、结构化布局、游戏引擎以及未来的生产能力都是可替换的 Tool 契约，而不是 AIPG Core 的硬编码依赖。

## 候选状态

当前分支为 `1.1.0-beta.1-candidate.2`。它是隔离的 Candidate Change，尚未被正式采用或发布。

- Python 包：`aipg-framework==1.1.0b1`
- 新导入与命令：`aipg`
- 兼容导入与命令：`guif`
- 视觉领域 Skill：`$game-ui-framework`
- 框架治理 Skill：`$aipg-framework`
- 继续支持 Workflow Schema v1 和 v2

重要文档：

- [版本迭代记录](CHANGELOG.md)
- [AIPG 架构](docs/AIPG_ARCHITECTURE.md)
- [详细用户蓝图与使用地图](docs/AIPG_USER_BLUEPRINT.md)
- [GUIF 到 AIPG 迁移指南](docs/MIGRATING_GUIF_TO_AIPG.md)
- [母版引导式分层创作](docs/MASTER_GUIDED_LAYER_WORKFLOW.md)
- [候选发布说明](docs/RELEASE_NOTES_AIPG_1_1_BETA1_CANDIDATE.md)
- [既有 GUIF 产品规格](docs/GUIF_PRODUCT_SPEC.md)
- [Candidate Change 工作流](docs/IMPROVEMENT_WORKFLOW.md)
- [支持策略](SUPPORT.md)

## 架构

```text
AIPG Core
├─ 意图与领域路由
├─ 工作流运行、检查点与恢复
├─ 审批与修订作用域
├─ Artifact 血缘与受保护源
├─ Host 与 Tool 路由
├─ Evidence 与 Review
├─ Candidate Change 与正式采用
└─ 受控导出

Domain Packs
├─ Framework Governance
└─ GUIF Visual Production
```

AIPG Core 只理解 Workflow、Stage、Artifact、Dependency、Constraint、Approval、Evidence、Revision 和 Export 等通用概念。按钮、透明通道、Theme、视觉层级等属于 GUIF。

未来的音频、文案、代码、视频和游戏内容领域可以注册自己的工作流、上下文、Artifact、Tool、检查标准与导出器。

Theme 不是 AIPG 顶层前置条件。AIPG 先判断领域与工作流，再由工作流声明所需上下文。

## 两个闭环

生产闭环：

```text
需求
→ 领域与工作流
→ 所需上下文
→ 生产契约
→ 审批
→ 真实 Host/Tool 执行
→ Artifact 与血缘
→ 确定性检查和语义检查
→ 必要时修订
→ 受控导出
```

框架迭代闭环：

```text
发现问题
→ 诊断
→ 候选方案
→ 隔离候选
→ 真实证据
→ 正式采用决策
→ 发布与刷新
→ 回归
→ 恢复生产
```

批准候选开发不等于批准正式采用、合并、发布或修改稳定 Tool 路由。元数据检查不能证明视觉质量或语义正确。

## GUIF 视觉生产领域

GUIF 继续提供：

- 效果图生成与编辑；
- 私有 Theme 和 Source 注册；
- 受保护的来源血缘；
- 真实语义视觉检查；
- 生产资源与引擎导出；
- 母版引导式分层创作。

### 母版引导式分层创作

母版效果图提供风格、布局、视觉层级和设计意图，但不要求逐像素匹配。

```text
Theme 与母版
→ 粗粒度语义层级分析
→ 层级计划审批
→ 从底层到顶层创作
→ 每层完成后回拼
→ 真实语义视觉检查
→ 层级作用域修订
→ 最终审批
→ 独立资源与 Manifest 导出
```

硬约束只保护功能职责、布局锚点、资源边界、必要内容、透明通道和输出契约。造型细节、材质、纹理、光照和装饰属于软指导。每层可以设置低、中、高三档创作自由度。

修改某一层时，GUIF 保留此前已批准的底层，只使当前层和下游合成失效。

## Workflow Manifest v3

新工作流可以声明：

```json
{
  "schema_version": 3,
  "id": "master-guided-layer-creation",
  "domain": "visual-production",
  "requires": ["theme", "master-reference"],
  "creation_direction": "bottom-to-top",
  "stages": [
    "master-approval",
    "layer-analysis",
    "layer-plan-approval",
    "progressive-layer-creation",
    "recomposition-review",
    "final-approval",
    "engine-export"
  ],
  "constraint_policy": {
    "master_role": "style-and-layout-guidance",
    "pixel_matching": false,
    "creative_freedom": "adaptive"
  }
}
```

## 开发

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

macOS 或 Linux 使用 `.venv/bin/python`。

## 隐私与真实性

真实 Theme、Prompt、源图、会话记录、凭据、私有路径、候选证据和生成产物默认保存在 Framework Git 与 Project Git 之外。公共测试和示例只使用完全虚构的内容。

AIPG 不伪造图片像素、Tool 可用性、语义检查、候选结果或导出成功。外部 Tool 的权限、费用、凭据和数据流必须明确披露。

## 兼容策略

AIPG 1.x 保留现有 `guif` 包、命令、Skill、Schema、私有存储变量、Theme 记录、Source 记录、Artifact 记录和 Candidate Change 契约。新的框架级集成使用 AIPG 命名，视觉领域集成可以继续使用 GUIF。

## License

MIT。
