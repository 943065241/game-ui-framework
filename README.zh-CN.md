# Game UI Framework（GUIF）

[English](README.md) | **简体中文**

GUIF 是一个本地优先、模型无关的游戏 UI 工作框架，用于规划、生产、审阅、导出和持续演进游戏 UI 工作。

## 当前状态

`v1.0.0-alpha.9` — 已具备 Runtime 契约、可组合的 Agent 与 Pipeline、项目 Context 加载、引擎 Adapter 导出、确定性校验、保护性编辑、Memory、Workflow、Project 和 Theme 等基础能力。

## 产品规格

中英文双语的持续迭代产品规格维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。

该文档定义了 GUIF 的产品预期、经验证的当前状态、缺失能力、开发阶段、非目标、风险、待验证问题和验收标准。任何改变 GUIF 产品方向或核心能力状态的迭代，都必须在同一个版本或 Pull Request 中同步更新该文档。

## 当前可用能力

- `guif init <project>` 创建项目工作区。
- `guif inspect [project]` 查看框架或项目状态摘要。
- `guif run "<requirement>" --project <project>` 通过 Runtime Contract 执行需求。
- `guif plan "<requirement>"` 生成现有的路由计划格式。
- `guif validate <project>` 校验项目语义、Theme、Workflow 和 Resource Manifest。
- `guif record <type> "<message>"` 保存可复用的项目知识。
- `guif resource-create`、`resource-show` 和 `resource-validate` 管理生产资源契约。
- `guif asset-validate <manifest> <asset>` 检查尺寸、格式、Alpha 和命名。
- `guif export <project> --target <engine>` 通过 Engine Adapter 校验、复制并准备资源。
- `guif compose-edit` 和 `guif qa-pixels` 用于保护并验证非目标像素。
- 测试目标覆盖 Python 3.10、3.11 和 3.12。

## 开发环境安装

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

## 面向 ChatGPT 的 Runtime 流程

GUIF 的预期主要入口，是通过 ChatGPT 或其他 Agent Host 接收自然语言任务：

```text
用户需求
  -> ChatGPT / Agent Host
  -> GUIF Runtime
  -> Project Context
  -> 已选择的 Pipeline
  -> 已注册的 Agent
  -> Task 结果
```

Runtime 本身不依赖 OpenAI 或任何其他模型提供方。Agent Host 可以直接调用：

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "制作中世纪港口商店页面",
    pipeline="ui-production",
)
print(task.to_dict())
```

对应的 CLI 命令：

```bash
guif run "制作中世纪港口商店页面" \
  --project LeekParty \
  --pipeline ui-production
```

## Runtime Contract

alpha.9 的 Runtime 是一个可执行的调度契约，还不是已经完成真实 AI 美术生产的 Worker。

```text
Runtime
  -> Context Loader
  -> Pipeline
  -> Agent Registry
  -> Task
```

默认 `ui-production` Pipeline：

```text
planner
  -> director
  -> theme
  -> resource
  -> prompt
  -> qa
  -> export
```

每个 Agent 接收并返回同一个可变 `Task`。Agent 之间不直接互相调用；只有 Runtime 通过 Registry 解析 Pipeline 的执行顺序。

当前内置 Agent 只执行契约层行为，包括记录生命周期事件、职责和状态变化。后续版本可以逐个替换为真实的 LLM、图片生成、Figma、GitHub、QA 或 Engine Integration，而不需要修改 Runtime 核心。

Runtime Context 当前会加载：

- `project.json`
- 已配置的当前 Project Theme
- Project Workflow Manifest
- Production Resource Manifest
- Project Memory 记录

## 快速开始

```bash
guif init LeekParty
guif run "制作交易按钮" --project LeekParty
guif resource-create trade-button-long button 264 134 png \
  --project LeekParty \
  --target-engine unity \
  --source source/trade-button-long.png \
  --import-settings '{"spriteMode":"Single","mipmapEnabled":false}'
guif export LeekParty --target unity
guif validate LeekParty
```

## Engine Adapter 层

通用 Exporter 会将引擎相关的准备工作交给不同 Adapter：

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

Adapter Registry 位于 `guif/adapters/`。核心 Exporter 负责校验和暂存资源；Adapter 负责生成引擎相关元数据。

当前行为：

- `generic`：复制通过校验的资源，不生成 Sidecar。
- `unity`：写入 `<asset>.guif-unity.json`，包含 Sprite 和 Mipmap 导入提示。
- `godot`：写入 `<asset>.guif-godot.json`，包含 Texture 导入提示。
- `unreal`：写入 `<asset>.guif-unreal.json`，包含 UI Texture Group 和 Mipmap 提示。

这些 JSON Sidecar 是 GUIF 生成的确定性元数据，不是各引擎原生生成的文件。

## 运行原则

1. 自然语言是主要用户界面；CLI 主要作为实现、调试和 CI 接口。
2. Git 是长期事实来源。
3. Runtime 调度保持模型无关。
4. Agent 不依赖或直接调用其他 Agent。
5. Effect Image 与 Production Asset 保持分离。
6. 引擎相关行为属于 Adapter，而不是 Framework Core。
7. 局部编辑通过基于 Mask 的合成保护非目标像素。
8. 只有 Feature、Test、CI、英文 README、中文 README、Version Metadata 和 Product Specification 保持一致时，一次发布才算完成。

## 仓库下一步方向

下一步将逐步替换仅有契约行为的 Agent，优先实现真实 Planner 和可持久化的 Task Run，同时保证 Runtime 在迁移过程中始终可用并保持模型无关。具体优先级与验收标准维护在 [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md)。
