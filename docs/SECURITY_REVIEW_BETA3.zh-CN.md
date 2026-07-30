# GUIF v1.0.0-beta.3 安全审查

Release：`v1.0.0-beta.3`  
Codex Plugin：`1.0.0-beta.3`  
Python Package：`1.0.0b2`  
Public API Version：`1`

## 审查范围

本审查覆盖 beta.3 的 Candidate Change、Tool Trial、正式采用、发布、插件刷新与回归工作流，重点检查授权边界、稳定版与候选版隔离、Tool 路由、证据完整性和私有数据处理。它不替代 beta.1、beta.2 对 Credential、Gateway Operation、Backup / Restore、外部保护、Migration、Pillow 兼容性和 Hash-only Release Provenance 的审查。

## 保持不变的安全属性

Beta.3 保持以下既有边界：

- 真实用户 Theme、Prompt、图片、Credential、Conversation Record、Runtime Evidence、Backup 和 Private Path 保存在公共仓库之外；
- GUIF 不伪造 Pixel、Tool 可用性、候选结果或语义视觉 Finding；
- Metadata 检查不能声称语义视觉质量已经通过；
- `dry-run` 只用于测试和开发，绝不是生产静默回退；
- Legacy `ProviderAdapter` 只能作为显式兼容路径；
- 公共示例与回归 Fixture 必须完全虚构；
- 公共兼容性继续由 Public API Version `1` 管理。

## 授权分离

改进工作流包含两个独立审批。

试验审批只授权隔离实验，不授权：

- 正式采用候选；
- Git 合并或发布；
- 替换稳定 Skill 或 Framework；
- 修改稳定的 Project / Workspace Tool 路由；
- 把候选产物描述为稳定生产结果。

只有存在真实候选证据后才能请求采用审批。发布或指定范围配置只能在正式采用后进行。

残余风险：Host 集成可能展示含义模糊的审批文案。Host 实现应明确区分试验与采用决策，并保存相应决策上下文。

## 稳定版与候选版隔离

Production Task 与 Improvement Case 是独立记录。候选工作执行期间，Production Task 保存在检查点。正式采用前，候选 Source、Configuration、Artifact 和 Evidence 不得覆盖稳定状态。

Code 与 Skill 候选在源码仓库开发环境运行，不修改已安装插件快照。Tool Trial 使用仅限当前 Task 的覆盖配置。只有明确采用并确认作用范围后，稳定的 Project / Workspace 路由才可以改变。

残余风险：外部开发 Tool 仍可能修改 GUIF 控制范围之外的文件。因此仍需 Repository Permission、Branch Protection、Review Policy 和 CI。

## Tool Discovery 与集成审查

Tool Trial 开始前，GUIF 会披露：

- 权限和数据范围；
- 外部调用和计费；
- Credential；
- Host 支持情况；
- 注册、可用性和健康状态。

不可用或未注册的 Tool 不能被描述为已成功完成真实试验，而应进入 Tool Integration 候选，并提供 Adapter、权限披露、Health Check、Result Callback、Failure Recovery 和 Contract Test。

残余风险：GUIF 可以记录披露内容与健康结果，但不能独立保证外部 Provider 的隐私、安全、计费准确性、服务可用性或模型行为。

## 证据完整性

候选采用必须有真实候选结果。视觉候选必须经过真实语义检查，仅靠 Metadata 不足以通过。候选证据与稳定基线证据保持分离，正式采用前候选 Artifact 不能标记为稳定生产输出。

适用时，GUIF 会记录候选 Branch、Commit、Version、Result 和 Publication Identity。这些记录提高可追溯性，但不构成 Cryptographic Attestation。Repository Signing、Trusted Builder 和第三方供应链验证仍属于独立控制。

## 发布与刷新边界

正式采用后，框架级变更进入发布阶段。工作流记录 Repository、Branch、Pull Request、Merge Commit 和最低插件版本。运行中的 Codex 会话不能声称已热加载新插件快照；用户必须刷新 Game UI Framework 并启动新会话，之后才能确认刷新。

暂停的 Production Task 恢复前，正式回归必须复现原始场景。

残余风险：回归可以覆盖被记录的场景，但不能证明不存在所有无关缺陷。仍需足够范围的 CI 与发布审查。

## 隐私审查

Improvement Case、候选证据、源图片、Prompt、私有开发 Handoff Bundle、Credential 和生成产物默认保持私有。真实私有材料不能复制到公共回归 Fixture，也不能提交到源码仓库。

Tool Trial 只有在已披露并获批准的 Tool 范围内，才能向外部服务传输用户数据。正式采用 Tool 不会静默扩大数据范围。

## 结论

Beta.3 通过分离授权阶段、隔离候选状态、要求真实证据、限制 Tool 路由作用范围，并在恢复生产前要求插件刷新与正式回归，加强了框架自我改进和 Tool 实验治理。它不能替代 Repository Control、可信外部 Tool、安全 Credential Custody、CI 或独立 Release Provenance。
