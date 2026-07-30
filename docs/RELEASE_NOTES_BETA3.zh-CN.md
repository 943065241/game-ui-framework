# GUIF v1.0.0-beta.3 发布说明

Release：`v1.0.0-beta.3`  
Codex Plugin：`1.0.0-beta.3`  
Python Package：`1.0.0b2`  
Public API Version：`1`

## 概要

Beta.3 将受治理的 Candidate Change 与 Tool Trial 工作流加入 GUIF 正式生产闭环。生产任务可以保存在安全检查点，由独立的 Improvement Case 诊断 Framework、Skill、Workflow、Theme Policy、Provider Routing 或 Tool 问题。候选方案必须依次经过试验审批、证据审阅、采用决策、发布或指定范围配置、必要的插件刷新，以及正式回归，原 Production Task 才能恢复。

本版本不会把“批准试验”解释为“批准采用、合并、发布、替换稳定 Tool 路由或覆盖稳定框架行为”。

## Candidate Change 工作流

GUIF 现在把框架改进记录为独立对象，与暴露问题的 Production Task 分离。

工作流支持：

- 在诊断和实验期间保存 Production Task 检查点；
- 对受影响层进行分类，而不是假定所有问题都是 Skill 缺陷；
- 记录实际行为、预期行为、诊断、候选改动、验证方案、隐私约束和完全虚构的公共回归 Fixture；
- 在隔离的源码仓库开发会话中构建代码或 Skill 候选；
- 关联候选 Branch、Commit 和 Version；
- 记录真实的稳定基线与候选证据；
- 要求用户明确选择正式采用、继续调整或放弃候选；
- 发布已采用的框架改动，并在恢复生产前执行正式回归。

## 两个相互独立的审批门

Beta.3 明确区分：

1. **试验审批**：只授权隔离实验。
2. **采用审批**：只有展示真实候选证据后才能进行。

两个审批不能互相推断。试验审批不授权 Git 合并、正式发布、稳定配置修改或插件替换。

## Tool Discovery 与隔离 Tool Trial

Tool 变更现在作为能力路由决策处理：

- 已注册、可用且健康的 Tool 可以进入仅限当前 Task 的试验；
- 试验期间稳定的 Project 与 Workspace 路由保持不变；
- 使用前必须披露权限、数据范围、外部调用、计费、凭据、Host 支持、注册状态、可用性和健康状态；
- 不可用或未注册的 Tool 会进入 Tool Integration 候选，而不是被伪装成成功试验；
- 不受支持的集成必须提供 Adapter、权限披露、健康检查、真实结果回调、失败恢复和契约测试。

正式采用的 Tool 路由只应用到用户确认的 Task、Project 或 Workspace 范围。

## 真实证据与视觉检查

没有真实候选结果，候选不能被采用。视觉候选还必须经过真实语义视觉检查。仅靠 Metadata 不能声称构图、可读性、Theme 一致性、降噪或可用性已经通过。

候选证据与稳定生产证据保持隔离。候选产物在正式采用前不能被描述为稳定生产结果。

## 发布、刷新与回归

已采用的 Code、Skill、Workflow、Theme Policy、Provider Routing 和 Tool Integration 改动会进入发布阶段。GUIF 会记录 Repository、Branch、Pull Request、Merge Commit 和最低插件版本。

需要刷新插件时，当前 Host 会话不能声称已经热加载。用户必须刷新 Game UI Framework 并启动新的 Codex 会话。正式回归随后复现原始场景；只有回归通过或用户明确放弃候选后，Production Task 才能继续。

## 兼容性

Public API Version 保持 `1`，Python Package 仍为 `1.0.0b2`。Beta.3 更新的是 Codex Plugin 工作流，不声称 Python Package 已升级。原有生产审批、Revision、语义检查、Gated Export、恢复、隐私和 Provenance 边界继续有效。

## CI 与验证

Beta.3 仓库报告：

- 177 个测试通过；
- 覆盖 Python 3.10、3.11、3.12；
- Wheel 与 Source Distribution 构建检查；
- Hash Provenance 生成与验证；
- 安装生成的 Wheel；
- CLI Contract 检查。

## 隐私

真实用户 Theme、Prompt、图片、Conversation Record、Credential、候选证据、私有开发 Bundle 和生成产物默认都保存在公共仓库之外。公共示例和回归 Fixture 必须完全虚构。
