# Portable AI Assets System — 开源定位与价值判断

## 一句话定位

**Portable AI Assets System** 不是又一个 agent 平台，而是一个面向多 agent、多模型、多客户端、多机器场景的 **AI 工作环境资产可迁移层**。

它的核心承诺是：

> 换工具、换模型、换客户端、换机器时，不必从零重建自己的 AI 工作环境。

它把下面这些内容，从“散落在各个 runtime 里的配置和记忆碎片”变成：

- 可版本化
- 可审计
- 可备份
- 可恢复
- 可跨 agent 迁移

的长期资产：

- 用户画像 / preferences
- 长期记忆摘要 / project summaries
- skills / prompts / playbooks
- workflow / capability manifests
- adapters / runtime projections
- bootstrap / rebuild policies
- secret-aware backup & restore flows

---

## 这个项目到底在解决什么问题

现状是：

- 每个 agent 都会“记住一点东西”
- 但没有一个 agent 的 memory 是完整真相源
- skills、plugins、MCP、workflow、prompt、adapter 又散落在不同目录和平台里
- 一换机器、一换客户端、一换模型，连续性就断裂

这个项目解决的不是“让单个 agent 更聪明”，而是：

## **让用户拥有自己的 AI 资产连续性，而不是被任一平台绑定。**

---

## Phase 69 public-facing thesis

对外叙事应尽量从“我做了一个资产同步工具”升级为“我在定义 AI 工作环境的可迁移资产层”。

推荐英文核心文案：

> Own your AI work environment instead of rebuilding it every time you change tools, models, clients, or machines.

对应的公开解释：

- **对象**：AI-native power users、indie hackers、小团队、多 agent 使用者
- **痛点**：记忆、skills、prompt、项目规则、MCP/tool binding、workflow、bootstrap 逻辑散落在多个 runtime
- **方法**：canonical assets + runtime projections + non-Git backups + review/report gates
- **边界**：不是 agent runtime、memory SaaS、workflow builder、MCP host、credential broker
- **信任基础**：public engine / private asset split、public safety scan、release readiness、capability governance

这部分已单独沉淀为：

- `docs/public-facing-thesis.md`

---

## 为什么它有价值

### 1. 它在解决一个真实且持续存在的问题

对于重度 AI 用户、独立开发者、小团队来说，真正痛的不是“没有模型可用”，而是：

- 我的 AI 助手为什么换个客户端就像失忆了？
- 为什么我的 skills / prompts / workflow 不能一起带走？
- 为什么我得一次次重新教 agent 我是谁、我怎么工作？
- 为什么已有机器和新机器之间没有安全迁移路径？

这类问题在现有生态里普遍存在，但通常只被局部解决。

---

### 2. 它切入的是“资产层”，不是“应用层”

现有大量项目在做：

- memory backend
- workflow builder
- chat UI
- local model runtime
- tool protocol

而本项目更像：

- AI 时代的 dotfiles
- AI 时代的 devcontainer + profile pack
- AI 时代的 personal/team AI asset layer

这意味着它的价值不在“替代现有平台”，而在：

## **让现有平台之间的迁移与连续性变得可控。**

---

### 3. 它天然适合本地优先、Git 友好、可审计场景

这类特性在开源生态里非常有吸引力：

- local-first
- Git-friendly
- diffable
- reviewable
- rollback-able
- secret-aware

这些属性使它对：

- power users
- indie hackers
- AI-native developers
- small AI teams

都很有吸引力。

---

## 外部相邻类别（不是完全同类，但高度相关）

### A. 记忆系统 / 长期记忆框架
相邻方向：
- MemGPT / Letta
- Supermemory
- LangChain / LlamaIndex memory modules

它们解决：
- “agent 如何记住东西”

它们通常不解决：
- skills/workflows/adapters/bootstrap 一起跨 runtime 迁移

---

### B. Prompt / workflow / agent builder
相邻方向：
- Dify
- Flowise
- Langflow
- GPTs / Claude Projects / 各类 prompt hubs

它们解决：
- “如何构建 agent 或 workflow”

它们通常不解决：
- “如何拥有自己的跨平台 AI 资产层”

---

### C. 本地 AI runtime / installer / workstation bootstrap
相邻方向：
- Ollama
- Open WebUI
- LocalAI
- Pinokio
- dotfiles / dev bootstrap 脚本

它们解决：
- “如何把环境装起来”

它们通常不解决：
- “如何把个人 AI 资产一起带着走”

---

### D. 协议与互操作层
相邻方向：
- MCP
- OpenAPI / plugin manifests
- 各种 agent framework protocol

它们解决：
- tool / resource 接入标准化

它们通常不解决：
- 个人/团队 AI 资产包标准化

---

## 结论：有没有真正同类？

### 有很多“邻居”，但很少有一个项目直接等于这个定位。

目前生态里：

- 有 memory
- 有 workflow
- 有 runtime
- 有 tool protocol
- 有 bootstrap

但缺少一个项目同时把这些整合成：

## **portable AI assets layer**

即：

- canonical source
- adapter projections
- drift-aware planning
- safe review/apply pipeline
- cross-machine continuity

这说明：

- 它不是无人区，但有明显空白
- 它的差异化是成立的

---

## 适不适合开源

### 结论：适合，但要开源“框架与层”，不是开源你的个人资产内容

建议开源：

- schema / manifest model
- bootstrap engine
- inspect / plan / diff / apply pipeline
- adapters framework
- merge candidate / review-assisted apply flow
- sample policies and templates
- redaction / secret boundaries

建议私有保留：

- 真实用户 memory
- 真实 profile
- 真实 runtime local instructions
- 私有 workflow / notes / summaries
- secrets / machine-local sensitive data

一句话：

## **开源引擎，不开源你的脑子。**

---

## 如果开源，它最强的价值主张应该是什么

### 1. 用户拥有自己的 AI 资产，而不是平台拥有

这是最能讲清楚的核心叙事：

> 你的记忆、技能、工作流、工具绑定，不该锁死在某一个客户端、某一个闭源平台、某一台电脑里。

---

### 2. 它不是又一个 AI 平台，而是跨平台资产层

推荐对外强调：

- 不替代现有 agent/runtime
- 作为它们上面的 portability layer
- 让现有生态更容易迁移、恢复、共享、版本化

---

### 3. 它可以成为“开放资产标准”的雏形

如果项目继续发展，最有潜力的不是“某个功能点”，而是：

- AI profile schema
- skills/workflow packaging format
- runtime adapter contract
- backup / restore policy layer

这会让项目从工具逐步接近“标准层”。

---

## 最可能的用户群

### 1. 重度个人 AI 用户
- 同时使用多个模型 / 客户端 / CLI agent
- 不想一换环境就丢失连续性

### 2. 独立开发者 / 开源黑客 / AI tinkerer
- 喜欢 local-first、Git、脚本化
- 愿意折腾 adapter / CLI / MCP / automation

### 3. 小型 AI 团队
- 希望共享 prompts、playbooks、tool presets、assistant profile
- 不想被单一平台锁死

### 4. 高度流程化的知识工作者
- 希望自己的 AI 协作环境能跨平台保持一致

---

## 最大风险

### 1. 定位太大
风险最大的是把它讲成：
- memory system
- agent framework
- workflow platform
- local runtime
- protocol standard

全部都想做。

建议坚持：

## **Portable AI Assets Layer**

这是当前最强、最清楚、也最不容易失焦的定位。

---

### 2. 跨 runtime 无法完全无损迁移
这不是 bug，而是现实。

更正确的说法应该是：

- 有 canonical layer
- 有 lossy/lossless adapter 差异
- 有 drift-aware review/apply
- 有人机协同的 reconciliation pipeline

本项目现在的方向其实已经很成熟地接受了这一点。

---

### 3. 安全与隐私边界必须长期维护
因为项目涉及：
- memory
- profile
- tool config
- machine-local state
- possible secrets

所以必须长期坚持：
- public/private/secret 分层
- redaction
- non-Git backup boundaries
- review-before-apply

---

## 推荐的开源切口

### MVP 不是“全能平台”，而是下面这几个核心件

#### 1. 资产 schema / manifest
- profile
- memory summary
- skills
- workflows
- adapters
- bootstrap policy
- secret references

#### 2. CLI / engine
- inspect
- plan
- diff
- apply
- merge-candidates
- review-apply

#### 3. 少量高质量 adapters
优先支持最有代表性的：
- CLI agent A
- CLI agent B
- 一个 workflow / MCP 类环境

#### 4. 安全边界
- redaction
- secret policy
- Git vs non-Git backup split

#### 5. 示例仓库与文档
- sample assets pack
- migration examples
- review/apply examples

---

## 现在这个项目已经具备的原型价值

当前原型已经不是想法文档，而是有一条完整链路：

- inspect
- plan
- safe apply
- diff
- merge-apply
- merge-candidates
- review-apply
- target-aware smarter draft synthesis

这意味着：

## 它已经可以作为一个真实 prototype 去讲故事、做演示、吸引早期用户。 

---

## 推荐的一句话对外介绍

### 中文
一个面向多 agent / 多模型 / 多机器场景的 AI 资产可迁移层，把记忆、技能、workflow、adapter、工具绑定和 bootstrap 变成可版本化、可审计、可恢复的长期资产。

### English
A portable AI assets layer for cross-agent, cross-model, and cross-machine continuity — versioning memory, skills, workflows, adapters, tool bindings, and bootstrap state as auditable, recoverable assets.

---

## 下一步建议

### 工程侧
- 继续做 normalized final draft / semantic merge cleanup
- 提升 adapters 的 target-specific merge quality
- 引入更正式的 schema / manifest validation

### 开源侧
- 做一个最小 public repo 版本
- 清理私有 memory/data
- 写清楚定位、边界、演示流程
- 先吸引“power user / AI-native dev”人群，而不是大众用户
