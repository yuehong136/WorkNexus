# WorkNexus 产品定位与 Vibe Coding 工程过程报告

> 本报告基于当前仓库文档、M0-M6 模块变更记录、路线图与工程规范整理。它描述的不是单个功能实现，而是从“开发一个类似 Jira 的产品”到形成 WorkNexus 产品定位、架构边界、AI 安全模型和持续开发流程的完整过程。

## 1. 报告摘要

WorkNexus 起点是“做一个类似 Jira 的项目协作与工单产品”。如果只沿着传统 Jira 路径推进，产品会自然落到项目、Issue、状态机、看板、成员、报表这些常规模块。但本项目从一开始处在 AI 应用平台已存在的背景下：本地已有 multirag 负责模型、RAG、智能体编排、工作流编排、MCP Client 和 Prompt 管理。因此，WorkNexus 的核心命题不是再做一个 AI 平台，也不是给工单系统加一个聊天框，而是回答一个更具体的问题：

**当 AI 参与企业工作流时，谁拥有业务数据，谁校验权限，谁确认动作，谁执行落库，谁负责审计追责？**

最终产品定位被收敛为：

> WorkNexus 是一个 AI-native 团队协作与工单 WorkOS，负责项目、工作对象、流程、Intake、AI WorkChat、Skills/MCP、权限和审计。multirag 负责“想和调度”，WorkNexus 负责“数据、权限、确认、执行、审计”。

这个定位决定了整个 v0.1 的开发顺序：先做身份、权限、项目和工作对象，再做 MCP 安全骨架，再做 WorkChat 与 AgentAction，最后做 Intake。也就是说，WorkNexus 不是从 UI 功能堆叠开始，而是从“AI 能否安全地提出并执行企业动作”这个闭环倒推数据模型、权限体系、接口契约和验证方式。

截至当前路线图，项目已推进到 M6 Intake 完成。M7 Dashboard 与 M8 Audit UI / Settings / Home 完善尚未开始。

## 2. 初始任务：从“类似 Jira”到“AI-native WorkOS”

### 2.1 传统 Jira 类产品的基本能力

“类似 Jira”的产品通常包含这些基础能力：

- 项目空间：项目、成员、角色、权限。
- 工作对象：Issue / Task / Bug / Requirement 等类型。
- 工作流：状态机、流转、负责人、优先级、截止时间。
- 协作：评论、活动记录、关系、看板。
- 入口：需求池、工单入口、外部反馈。
- 管理视图：统计、报表、审计、设置。

这些能力构成了 WorkNexus 的基础骨架：M2 Projects、M3 Work Items、M6 Intake、M7 Dashboard、M8 Audit / Settings / Home 都来自这一类产品的自然拆分。

### 2.2 调研对象与取舍

调研阶段没有采用“照搬某个产品”的方式，而是将不同产品拆成可借鉴的能力维度：

| 参照对象                   | 主要观察                                                                       | 对 WorkNexus 的影响                                                       |
| -------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| Jira / Atlassian           | 成熟的项目管理、Issue tracking、工作流、报告与企业治理能力                     | 确认项目、工作项、状态机、权限、审计、报表是基本盘                        |
| Linear                     | 现代产品研发工具强调速度、低噪音、工程团队体验，并开始把 AI 工作流纳入产品叙事 | 前端体验避免传统后台系统的臃肿，优先做清晰的列表、抽屉、看板和快速操作    |
| Plane                      | 开源 Jira / Linear 替代品，覆盖 issue、cycles、roadmaps 等产品研发管理场景     | 参考 IAM、成员页、活动 feed、抽屉详情、看板等交互与数据建模，但不照搬实现 |
| Dify / multirag 类 AI 平台 | AI 平台擅长模型、RAG、Workflow、Agent、工具调用和 Prompt 管理                  | 明确 WorkNexus 不重复做 AI 编排，只通过薄 AI Adapter 与 MCP 暴露业务能力  |

这一步最关键的结论是：**Jira 类产品解决“人如何组织工作”，AI 平台解决“模型如何推理和调度”，WorkNexus 要解决“AI 如何被允许参与人的工作系统”。**

因此，WorkNexus 没有把产品定位写成“AI Jira clone”，而是进一步抽象为“AI-native 协作与工单 WorkOS”。

## 3. 产品定位决策

### 3.1 不做什么

明确边界是本项目能稳定推进的前提。v0.1 明确不做：

- 不做模型管理、RAG、Agent 编排、Workflow 编排、Prompt 管理。
- 不做完整动态 RBAC、组织树、SSO 实接、审批流、Cycle/Sprint、Gantt/Roadmap、自动化引擎。
- 不做完整 IM、移动端、文档知识库、Dashboard Builder、Data Apps。
- 不让 AI 直接绕过 WorkNexus 的权限与审计落库。
- 不把 AI 平台返回的权限判断当作可信结论。

这些“不做”不是功能不足，而是产品边界。它保证 v0.1 的精力集中在 AI 安全参与业务工作流的最小闭环。

### 3.2 做什么

WorkNexus 的职责被固化为五个关键词：

| 关键词 | 含义                                                                                       |
| ------ | ------------------------------------------------------------------------------------------ |
| 数据   | 项目、工作项、Intake、消息、AgentAction、SkillInvocation、AuditLog 是 WorkNexus 的系统记录 |
| 权限   | 所有业务读取和写入都由 WorkNexus 自己校验，前端和 AI 平台都不能绕过                        |
| 确认   | AI 产生的写动作先成为 AgentAction，按风险等级由人确认                                      |
| 执行   | 业务写入统一通过 service 层执行，而不是由 MCP tool 或路由直接写库                          |
| 审计   | 工作项变化、AI 建议、用户确认、Skill 调用、权限变化等都可追溯                              |

### 3.3 一句话定位

对外表述可以收敛为：

> WorkNexus 是一个 AI-native WorkOS，用于把 AI 建议转成可权限校验、可人工确认、可执行落库、可审计追责的团队工作。

这句话比“类似 Jira”更准确，因为它表达了本产品相对传统工单系统的核心差异：AI 不只是聊天入口，而是可参与业务动作，但必须被治理。

## 4. 系统边界与总体架构

### 4.1 WorkNexus 与 multirag 的职责切分

| 系统      | 负责内容                                                                    |
| --------- | --------------------------------------------------------------------------- |
| multirag  | 模型管理、知识库/RAG、智能体编排、工作流编排、MCP Client、Prompt 管理       |
| WorkNexus | 项目、工单、流程、Intake、仪表盘、权限、审计、业务数据落库、Skills/MCP 暴露 |

这条边界贯穿所有模块。WorkChat 不是在 WorkNexus 内重新做 Agent，而是由 WorkNexus 生成权限过滤后的上下文、签发 delegation token、调用 multirag，再把 multirag 回调 WorkNexus MCP 所产生的低风险写动作转为 AgentAction。

### 4.2 架构形态

WorkNexus 采用 monorepo：

```text
apps/web        React 19 + Vite + Tailwind 4 frontend
apps/server     FastAPI + FastMCP backend
packages/contracts
                OpenAPI -> orval generated TypeScript client
infra/docker    PostgreSQL local stack
docs            roadmap, modules, workflow, specs
```

后端是模块化单体，而不是一开始拆微服务。原因是 v0.1 的复杂度主要来自跨模块事务、权限和审计，如果过早拆服务，会让 AgentAction、SkillInvocation、AuditLog、WorkItem、Intake 之间的事务一致性变复杂。

前端采用 feature-based 切片，避免页面随模块增多失控。API 类型由后端 OpenAPI 生成，避免手写类型漂移。

### 4.3 核心数据闭环

v0.1 验收链路可以概括为：

```text
setup owner
  -> login
  -> create project
  -> invite member
  -> create work item
  -> board transition
  -> WorkChat calls multirag
  -> AI calls WorkNexus /mcp low_write tool
  -> WorkNexus creates AgentAction(pending)
  -> user approves
  -> service writes business data
  -> skill_invocations and audit_logs record the chain
  -> dashboard can consume the updated data
```

这个闭环说明，WorkNexus 的 MVP 不是“有几个页面”，而是“AI 写动作是否能被安全地提案、确认、执行和追溯”。

## 5. 核心产品与安全设计

### 5.1 Identity 是所有模块的前置

M1 不是普通登录模块，而是后续 AI 安全链路的根：

- server-side session + HttpOnly Cookie，浏览器不保存 session token。
- 固定 6 个系统角色：`owner/admin/project_admin/member/viewer/ai_agent`。
- 权限矩阵用代码常量维护，v0.1 不建动态 roles/permissions 表。
- `project_members` 只保存用户项目角色，`role_bindings` 保存 tenant 级授权、AI Agent 授权和特殊授权，禁止双写。
- delegation token 代表“AI 当前代表哪个用户、哪个 agent、哪个项目、哪个 conversation/run”。
- audit 从 M1 起横切落地，而不是最后补。

这使得后续 M4/M5 的 MCP 与 AgentAction 能建立在真实身份和权限上下文上，而不是临时拼接 user_id。

### 5.2 WorkItem 是业务执行的核心对象

M3 把传统工单系统的基本盘落地：

- 8 种类型：task、requirement、bug、risk、decision、approval、incident、feedback。
- 固定 Workflow Lite 状态机。
- 评论、活动时间线、关系、看板。
- `source/source_ref_id` 记录来源，区分 manual、ai_chat、intake、mcp、api。
- 状态流转同时写业务活动和安全审计。

一个关键取舍是：工作项的 AI 来源不允许由客户端请求体伪造，而是由 service 根据入口派生。这是 AI 参与场景下的 provenance 设计。

### 5.3 MCP 是业务能力暴露层，不是绕过系统的后门

M4 把 WorkNexus 的业务能力暴露给 AI 平台，但同时设定了强约束：

- `/mcp` 入口必须双 token：server token 证明来自 multirag，delegation token 证明代表哪个用户。
- 每个 tool 都有风险 tag：`read/low_write/high_write`。
- 每次调用都写 `skill_invocations`。
- tool 内不能自己读 header、不能用参数当身份依据，只能从统一 MCP context 取 actor 和 delegation。
- M4 时期 low_write 被阻断，等 M5 AgentAction 确认链路上线后才允许 defer 成待确认动作。

这一步把“AI 可以调用工具”从能力问题变成治理问题：不仅要能调，还要知道谁调、代表谁、调了什么、风险是什么、结果如何。

### 5.4 AgentAction 是 AI 写动作的治理对象

M5 的核心不是聊天 UI，而是 AgentAction：

- AI 提案唯一主路径是 MCP low_write tool call。
- WorkNexus 不解析模型文本中的 proposed_action，避免把自然语言当作可信执行协议。
- low_write tool call 由中间件归一化成 `AgentAction(status=pending)`。
- 用户批准后，后端实时重跑双重校验。
- 执行时显式 dispatcher 调 service 层，不重放 MCP HTTP，不直接调用 tool body。
- 业务写入用 AI Agent actor 执行，但创建工作项等用户字段要记录真实 requested_by_user_id。

这将 AI 写动作拆成三个阶段：提出、确认、执行。每个阶段都有独立记录和审计。

### 5.5 Intake 把“需求入口”纳入 AI 工作流

M6 将传统需求池 / 请求池落到 WorkNexus：

- 请求先进入项目级 Intake inbox。
- 规则版 TriageEngine 同步生成 advisory 建议。
- AI 建议只做展示和表单预填，绝不自动采纳。
- accept 是单步原子操作：同一事务创建 WorkItem，并回填 Intake 状态。
- AI 可提案 create / accept intake，但仍走 AgentAction 确认链。

Intake 的意义是把“还不是工作项的输入”纳入治理闭环。它既支持人的手工分诊，也给未来 AI 分流、去重、分类留下空间。

## 6. Vibe Coding 的组织方式

### 6.1 本项目的 vibe coding 定义

这里的 vibe coding 不是“随意让 AI 写代码”，而是：

> 以 AI 编码代理作为主要生产力，但把产品决策、工程规范、模块设计、上下文读取、测试验证和 PR 收口全部文档化，使每次 AI 开发会话都能从同一套事实和约束出发。

核心思想是：**把上下文从聊天窗口迁移到仓库文档里，把临场提示词变成可复用的工程协议。**

### 6.2 上下文真相源

每次开发会话必须按顺序读取：

1. `AGENTS.md`：唯一工程规范真相源。
2. `docs/roadmap.md`：全局蓝图、模块进度、已敲定决策。
3. 对应 `docs/modules/<module>.md`：当前模块的目标、边界、模型、API、MCP、UI、测试点、变更记录。

如果模块文档不存在，第一步不是写代码，而是从 `_template.md` 创建模块文档。这保证每个模块先有设计边界，再有实现。

### 6.3 任务派发模板

仓库中 `docs/prompts/task-kickoff.md` 把“派发给无上下文 AI 会话”的提示词固定下来。它不承载大段业务背景，而是引导新会话读取仓库文档，并强调：

- 开工前必读链不可跳过。
- 有疑问先讨论，不靠假设开发。
- 同场景只允许一种写法。
- 文案必须 zh-CN / en-US 双语。
- 接口变更后运行 contracts generate。
- 完成标准包含测试、文档变更记录和 roadmap 更新。

这解决了 vibe coding 常见的上下文漂移问题：不是把所有背景塞进提示词，而是让提示词指向稳定文档。

### 6.4 模块文档的作用

每个模块文档都不是“事后总结”，而是开发过程的控制面：

- 定义目标和明确不做。
- 固化数据模型和状态机。
- 列出 REST API 与 MCP tools。
- 明确审计事件和权限点。
- 约定 UI 路由和组件形态。
- 写测试点。
- 每个 PR 追加变更记录。

例如 M5 WorkChat 文档先敲定 A-H 决策，再拆成后端核心、AI Adapter、contracts、前端、E2E。M6 Intake 也先敲定 A-H 决策，再实现模型、规则引擎、MCP、前端和 E2E。

### 6.5 “统一写法手册”控制代码风格分裂

AGENTS.md 中的前后端统一写法手册是控制多次 AI 生成代码风格分裂的关键。它规定：

- 查询必须放在 feature api hook 和 Key Factory 中。
- 变更必须用 mutation hook，并按 Key Factory invalidate。
- 空/错/加载三态统一用 patterns。
- 表单统一 react-hook-form + zod + shadcn Form。
- 确认操作统一 ConfirmDialog。
- 详情长表单用 Sheet。
- 表格列定义独立 columns.tsx。
- 路径集中 `lib/paths.ts`。
- AI / Markdown 内容统一走 `lib/markdown.tsx` sanitize。
- SSE 统一走 `lib/sse.ts`，禁止页面内裸 fetch 流。
- AgentActionCard 是确认动作的唯一卡片形态。
- TriageSuggestionCard 是只读 advisory 建议的唯一卡片形态。

这让不同开发会话写出的代码保持同一套语言，而不是每个 agent 发明一套模式。

## 7. 标准开发循环

项目形成的标准循环是：

```text
读 AGENTS.md
  -> 读 roadmap
  -> 读/建 module doc
  -> 敲定设计疑问
  -> 后端模型/迁移/schema/service/router/mcp
  -> 后端测试
  -> contracts:generate
  -> 前端 api hooks/components/routes/i18n
  -> 前端测试
  -> E2E 主链路
  -> 更新模块变更记录与 roadmap
```

这个循环有几个特点：

1. **先设计后实现。** M5/M6 都先通过文档敲定 A-H 决策，再进入代码。
2. **后端先行。** 数据模型、服务层、权限、审计和测试先落地，前端通过 contracts 跟进。
3. **契约生成隔离。** OpenAPI 变化后用 orval 生成 TypeScript client，避免前端手写类型。
4. **前端按 feature 切片。** 每个模块的 api hooks、components、routes、stores 分离，避免跨 feature import。
5. **测试即完成定义。** 没有测试和文档变更记录，PR 视为未完成。

## 8. 验证体系

### 8.1 后端验证

后端验证强调真实边界：

- service 层测试使用真实 PostgreSQL 与事务回滚 fixture。
- REST 测试使用 `httpx.AsyncClient` + `ASGITransport`。
- MCP tools 使用 FastMCP in-memory Client。
- Alembic 迁移要求 upgrade/down/check 干净。
- 关键纯函数单测覆盖权限矩阵、状态机、SSE frame 解析、TriageEngine 等。
- 审计和业务写入要求同事务验证，失败不能只看 API 返回。

### 8.2 前端验证

前端验证强调用户路径和状态一致性：

- vitest + Testing Library 覆盖 hooks、stores、复杂组件交互。
- msw mock API，验证 query/mutation 行为。
- Playwright 覆盖主链路，例如 setup/login、项目成员、工作项、看板、WorkChat、Intake。
- i18n 和主题切换作为 E2E 重要路径保持可用。
- 构建、lint、typecheck 是前端收口门槛。

### 8.3 AI 链路验证

AI 链路的特殊性在于外部 multirag 端点可能不稳定或尚需 live-verify，因此项目采用双轨策略：

- 产品设计以真实 multirag adapter 为目标。
- 测试/E2E 使用 `FakeAIClient`，保证 CI 与本地验证确定性。
- 对真实 multirag path/body/header/SSE envelope 保留 live-verify 开放项，不把未验证接口写成既成事实。
- 所有 AI 写动作仍通过 MCP -> AgentAction -> approve -> service 的链路验证，而不是让 fake client 直接写库。

这避免了 AI 外部依赖不稳定导致产品主链路无法验证。

## 9. M0-M6 阶段复盘

### M0 Scaffold

目标是把仓库从规范推进到可运行骨架：

- React 前端可启动。
- FastAPI 同进程挂载 REST `/api/v1` 和 MCP `/mcp`。
- PostgreSQL compose 可用。
- OpenAPI contracts 管线可用。
- 基础健康检查和 MCP ping 可验证。

M0 的价值是先建立工程通道，而不是马上写业务页面。

### M1 Identity & Access

M1 建立全部安全地基：

- 10 张身份/权限/审计相关表。
- setup、login、logout、me、users、invites。
- server-side session 与 HttpOnly Cookie。
- 角色权限矩阵与 `core/access.py`。
- delegation token 签发和校验。
- 审计 service 与 request_id。
- 前端 auth、settings members、路由守卫、PermissionGate。

这一步使后续所有项目级、AI 级动作都有统一主体和权限判断。

### M2 Projects

M2 落地项目空间：

- 项目 CRUD 与归档。
- 项目成员管理。
- 项目列表按可见性过滤。
- 项目概览基础信息。
- 成员变更审计。

这里刻意不做工作项统计，因为它依赖 M3。这个“不放假 0”的取舍体现了文档驱动开发的边界意识。

### M3 Work Items

M3 是传统工单能力的核心：

- 4 张工作项相关表和 project sequence。
- 8 类型、固定状态机、custom fields 轻校验。
- 评论、活动、关系、软删除。
- 概览统计。
- 6 个 workitem MCP tools。
- 前端列表、详情抽屉、评论、关系、看板。

M3 后，WorkNexus 已经具备一个基础 Jira/Linear 类产品的核心工作对象能力。

### M4 Skills / MCP

M4 把 AI 调用业务工具的入口安全化：

- `skill_invocations` 表。
- `/mcp` 双 token 中间件。
- 风险门禁。
- tool tag 反射和 `/skills` 页面。
- read 工具执行，low_write 在 M4 阶段阻断。

这是从“系统能被 AI 调用”到“系统能治理 AI 调用”的转折。

### M5 WorkChat + AgentAction

M5 打通 AI 对话与确认执行：

- conversations/messages/agent_actions 三表。
- low_write MCP tool call defer 成 AgentAction。
- approve/reject REST。
- dispatcher 调 work_items service。
- AIClient 抽象、FakeAIClient、multirag adapter skeleton。
- WorkNexus 自有 SSE 事件 schema。
- 前端 AIChatPanel 与 AgentActionCard。
- E2E 覆盖 AI 提案 -> 用户确认 -> 工作项落库。

这一步是 WorkNexus 从传统工单系统升级为 AI-native WorkOS 的关键。

### M6 Intake

M6 把请求池和分诊能力补齐：

- intake_requests 表与状态机。
- RuleBasedTriageEngine。
- accept 原子转换为 WorkItem。
- reject / duplicate / snooze。
- intake MCP tools 接入 AgentAction dispatcher。
- 前端 inbox、详情 Sheet、TriageSuggestionCard、ConvertToWorkItemDialog。
- E2E 覆盖提交 intake -> 分诊 -> 接受转工作项。

M6 后，WorkNexus 不仅能管理已有工作，还能接收并治理新需求入口。

## 10. 工程质量控制机制

### 10.1 文档即上下文

AI 编码代理最大的问题不是不会写代码，而是会在缺上下文时做错假设。本项目通过以下方式减少错误假设：

- AGENTS.md 固化全局规范。
- roadmap 固化产品范围和 D1-D9 决策。
- module docs 固化模块细节。
- task-kickoff 模板约束新会话读取顺序。
- PR 变更记录保留每个模块的真实演进轨迹。

### 10.2 单一真相源

项目坚持多处单一真相源：

- 工程规范：AGENTS.md，CLAUDE.md 是镜像。
- 路线与决策：docs/roadmap.md。
- 技术栈版本：docs/tech-stack.md。
- API 类型：OpenAPI -> packages/contracts。
- 主题 token：Tailwind 4 CSS variables。
- 语言偏好：zustand ui store。
- 权限判断：core/access.py。
- 写库入口：module service.py。
- AI 动作确认：AgentAction。

这种设计降低了 vibe coding 中“同一场景多种写法”的风险。

### 10.3 一 PR 一意图

复杂模块按 PR 拆分。例如 WorkChat：

1. 设计文档。
2. 后端核心和 AgentAction。
3. AI Adapter 与 runs。
4. contracts。
5. 前端与 E2E。

这种拆法让每个阶段有明确验收点，也便于 AI 代理在上下文窗口有限时专注单一意图。

### 10.4 生成产物和手写代码分离

接口变化后生成 contracts，但不手写/手改生成产物。这样前后端契约漂移能被工具发现，而不是靠人记忆。

### 10.5 新场景先补手册

当出现新场景，例如：

- Markdown 渲染。
- 看板拖拽。
- AI SSE。
- AgentActionCard。
- advisory TriageSuggestionCard。
- MCP tool 鉴权与留痕。

项目先补 AGENTS/CLAUDE 手册条目，再写业务代码。这样后续模块不会重复发明新写法。

## 11. 阶段成果

截至 M6，WorkNexus 已具备：

- 可运行 monorepo 工程骨架。
- 身份、会话、权限、邀请、delegation token。
- 项目空间和成员管理。
- 工作项、评论、活动、关系、看板。
- MCP 安全网关和 SkillInvocation 留痕。
- WorkChat、AI SSE、AgentAction 确认执行。
- Intake 请求池、规则分诊、接受转工作项。
- 双语前端、语义主题、contracts、测试与 E2E 主链路。

从产品角度看，当前已经不是简单 demo，而是一个能演示核心闭环的 v0.1 半成品：人和 AI 都围绕同一套项目/工作项/请求池数据工作，但 AI 写动作被权限、确认和审计约束。

## 12. 当前遗留与后续方向

### 12.1 已知遗留

- M7 Dashboard 未开始。
- M8 Audit UI / Settings / Home 完善未开始。
- multirag 真实 `/api/v1/agents/{agent_id}/completions` endpoint/body/header/SSE envelope 仍需 live-verify。
- AI 连接设置页 v0.1 仍是只读脱敏展示方向，未做可写配置。
- 部分模块文档顶部状态仍显示“设计中/开发中”，但 roadmap 已记录 M5/M6 完成，后续可统一整理文档状态。

### 12.2 后续建议

1. **先做 M7 Dashboard。** 让项目、工作项、Intake、AI 创建数、逾期、高优先级、转化率形成可见经营视图。
2. **再做 M8 Audit UI。** 当前审计已横切落库，但需要查询 UI 把“可追溯”变成用户能看见的能力。
3. **补真实 multirag live verification。** 把 FakeAIClient 验证过的链路对接真实 AI 平台，记录 endpoint/body/header 差异。
4. **整理模块文档状态。** 将已完成模块顶部状态与 roadmap 对齐，减少未来会话误判。
5. **将本报告拆出对外版本。** 内部版保留工程细节；对外版可压缩为产品设计复盘或项目申报材料。

## 13. 方法论总结

WorkNexus 的开发过程说明：vibe coding 可以用于复杂产品，但前提是不能把所有控制权交给即时提示词。真正有效的方式是建立一套“AI 代理可读、可执行、可验证”的工程环境：

- 用 AGENTS.md 定义全局工程契约。
- 用 roadmap 定义产品边界和决策。
- 用 module docs 定义模块级设计。
- 用 task-kickoff 模板让新会话从正确上下文启动。
- 用 service 层、contracts、tests、E2E 把 AI 生成代码约束在可验证边界内。
- 用变更记录保留每个阶段为什么这么做、做了什么、验证了什么。

从“开发一个类似 Jira 的产品”到 WorkNexus，真正的产品创新不在于重新实现 issue tracking，而在于把传统工作管理系统改造成 AI 可以参与、但不能越权的执行底座。

## 参考资料

### 项目内资料

- [AGENTS.md](../AGENTS.md)
- [README.md](../README.md)
- [docs/roadmap.md](roadmap.md)
- [docs/development-workflow.md](development-workflow.md)
- [docs/tech-stack.md](tech-stack.md)
- [docs/reference/v0.1-feature-spec.md](reference/v0.1-feature-spec.md)
- [docs/prompts/task-kickoff.md](prompts/task-kickoff.md)
- [docs/modules/identity.md](modules/identity.md)
- [docs/modules/projects.md](modules/projects.md)
- [docs/modules/work_items.md](modules/work_items.md)
- [docs/modules/skills.md](modules/skills.md)
- [docs/modules/workchat.md](modules/workchat.md)
- [docs/modules/intake.md](modules/intake.md)

### 外部参照

- [Atlassian Jira](https://www.atlassian.com/software/jira)
- [Atlassian Jira features](https://www.atlassian.com/software/jira/features)
- [Linear](https://linear.app/)
- [Plane GitHub README](https://github.com/makeplane/plane)
- [Dify GitHub README](https://github.com/langgenius/dify)
- [Dify Docs Introduction](https://docs.dify.ai/en/use-dify/getting-started/introduction)
