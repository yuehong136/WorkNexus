# WorkNexus 开发大纲（Roadmap）

> **本文件是每个开发会话的导航与共识文件。**
> 每次开发（人类或 AI 代理）必须按以下顺序进入工作：
> 1. 读 `AGENTS.md`（工程规范）
> 2. 读本文件（全局蓝图 + 当前进度 + 已敲定决策）
> 3. 读或创建对应的 `docs/modules/<module>.md`（底稿见 `docs/reference/v0.1-feature-spec.md`）
> 4. **对范围、设计、细节有任何疑问，先与用户讨论敲定，再动手开发**
> 5. 开发完成后在同一 PR 内更新模块文档与本文件的进度/变更记录
>
> 本文件只记录"做什么、边界、已敲定的决策"，不写实现细节（实现细节在各模块文档与功能规格书）。
> 大纲本身的变更（范围、顺序、决策）必须经用户确认。

---

## 1. 产品定位

WorkNexus（智协中枢）：AI-native 团队协作与工单 WorkOS。v0.1 不是"带 AI 的工单系统"，而是**能让 AI 安全参与企业工作流的协作底座**——优先保证权限链路正确、AI 身份链路正确、业务数据归 WorkNexus 所有、multirag 只负责智能能力、AI 写动作必须确认和审计。

边界（详见 AGENTS.md 第 1 节）：已有 AI 平台（multirag）负责"想和调度"（模型、知识库、智能体编排、MCP Client）；WorkNexus 负责"数据、权限、确认、执行、审计"，并通过 `/mcp` 把业务能力暴露给 AI 平台。

## 2. v0.1 目标闭环（验收标准）

完整 16 步验收链路见 `docs/reference/v0.1-feature-spec.md` 第 12 节，主干：

```text
首启 /setup 建 owner → 登录 → 创建项目 → 邀请 member（权限隔离生效）
  → 创建工作项 → 看板流转 → AI WorkChat 调真实 multirag（SSE）
  → AI 返回 proposed_action → 生成 AgentAction → 用户确认 → 落库
  → skill_invocations 留痕 → audit_logs 记录建议/确认/执行全链 → 仪表盘统计更新
```

闭环全链路打通 + Playwright E2E 覆盖，即 v0.1 完成。

## 3. 模块总览与进度

| # | 模块 | 后端 module | 前端 feature | 状态 | 模块文档 |
| --- | --- | --- | --- | --- | --- |
| M0 | 脚手架 | `worknexus` 骨架 | `app/` 骨架 | **已完成** | [scaffold.md](modules/scaffold.md) |
| M1 | Identity & Access | `identity`（+ `audit` 起步） | `auth`、`settings/members` | **已完成**（PR1 模型/setup/会话、PR2 权限/me/邀请/delegation、PR3 前端+E2E） | [identity.md](modules/identity.md) |
| M2 | 项目空间 | `projects` | `projects` | **已完成**（PR1 后端 CRUD/归档/成员管理 + PR2 前端列表/概览/成员管理 + E2E） | [projects.md](modules/projects.md) |
| M3 | 工作对象 + Workflow Lite + 看板 | `work_items` | `work-items`、`board` | **已完成**（PR1 后端核心 + PR2 评论/活动/关系 + PR3 概览统计/MCP + PR4 前端 List + PR5 WorkItemDrawer + PR6 看板/E2E） | [work_items.md](modules/work_items.md) |
| M4 | Skills / MCP 骨架 | `skills` | `skills` | **已完成**（仅骨架 + workitem-skill：PR1 文档 + PR2 后端 /mcp 双 token 中间件 + skill_invocations 留痕 + GET /skills/invocations + 回填 workitem-skill + PR3 contracts + PR4 前端 /skills 页；project/report 余力、knowledge→M5、intake→M6 推迟） | [skills.md](modules/skills.md) |
| M5 | AI WorkChat + AgentAction | `workchat`（含 agent_actions、AI Adapter） | `workchat` | **已完成**（PR1 设计敲定 A–H；PR2 后端核心：conversations/messages/agent_actions + service〔提案/approve 实时双重校验 + dispatcher 以 AI Agent actor 执行/reject/list〕+ REST + 改 skills 中间件 low_write defer 建 AgentAction + 7xxx + AuditAction；PR3 AI Adapter〔AIClient 抽象 + parse_sse_frame 纯函数 + FakeAIClient + MultiragAgentCompletionsClient（待 live-verify）〕+ /workchat/runs SSE 代理 + D6 上下文过滤；PR4 contracts；PR5 前端 lib/sse.ts + AIChatPanel/AgentActionCard + i18n + E2E 主链路。后端 167 tests、前端 26 tests、E2E 1 全绿。**遗留**：multirag 真实 endpoint live-verify〔workchat.md §11〕、AI 连接设置页只读展示） | [workchat.md](modules/workchat.md) |
| M6 | Intake | `intake` | `intake` | **已完成**（PR1 设计 A–H；PR2 后端核心〔模型/迁移/规则 TriageEngine/状态机/原子 accept-convert/REST/3xxx/审计〕；PR3 intake MCP 子服务器 + 接入 M5 AgentAction dispatcher〔create/accept_intake_request〕；PR4 contracts；PR5 前端 inbox/分诊页〔DataTable + Sheet 抽屉 + TriageSuggestionCard + ConvertToWorkItemDialog + reject/duplicate/snooze〕+ E2E 主链路。后端 204 tests、前端 28 tests、E2E 1 全绿） | [intake.md](modules/intake.md) |
| M7 | 仪表盘 | `dashboards` | `dashboard` | **已完成**（PR1 设计 A–H；PR2 后端核心：领域 metrics read-model〔work_items/intake〕+ M3 summary 重构复用同口径 + dashboards service/insights/4 REST 端点 + 规则版 InsightsEngine，无新表/迁移；PR4 contracts；PR5 前端：recharts 图表封装〔BarChart/DonutChart/LineChart + lib/chart-colors CSS 变量取色〕+ DashboardCards/分布/趋势/workload/overdue/AI 洞察卡 + 入口按钮 + i18n + E2E 主链路〔创建工作项→仪表盘数字随之更新〕；PR3 只读 MCP 工具 `dashboard_get_project_dashboard`〔read tag·delegation 取项目·snapshot 复用领域 read-model·skill_invocations 留痕〕。后端 228 tests、前端 31 tests、E2E 7 全绿） | [dashboard.md](modules/dashboard.md) |
| M8 | 设置与审计 UI + 工作台完善 | `audit` 完善 | `settings`、`audit`、`home` 完善 | 未开始 | 待建 |

依赖关系：M1 是所有模块的前置（身份、权限、审计、AI Agent 身份、delegation token）；M3 依赖 M2；**M4 先于 M5**（`/mcp` 双 token 校验与 skill_invocations 是 AgentAction 执行链路的依赖）；M6 依赖 M3/M5；M7/M8 依赖前序数据。审计从 M1 起横切落地，M8 只做查询 UI 收尾。

## 4. 已敲定的关键决策（开发前必读）

### D1 技术栈与工程规范

见 `AGENTS.md`（版本定版、目录分层、统一写法手册、PR 规范）。提交信息一律英文。

### D2 认证与会话（v0.1）

- 本地账号（邮箱+密码，bcrypt）+ 邀请制（v0.1 复制邀请链接，不接邮件）+ `/setup` 首启初始化（建 owner、default tenant、种子角色、默认项目、默认 AI Agent，完成后封禁）。
- **Server-side session + HttpOnly Cookie**（Secure[prod]、SameSite=Lax、7 天、DB 只存 token hash）。禁止把会话 token 放 localStorage。前端 fetch 一律 `credentials: 'include'`。
- SSO/OIDC 不做但预留：`users.identity_provider`（`local | multirag | oidc`）+ `users.external_user_id`（映射 multirag 用户，32 hex）。
- 登录后 `GET /api/v1/me` 返回 `CurrentUserContext`（user + tenant + roles + permissions + 项目级权限 + 可用 AI Agents），前端只据此控制菜单/按钮，**不自己推导权限**；后端永远强制校验。

### D3 权限模型（精简 RBAC，v0.1）

- **不建** roles / permissions / role_permissions 表。6 个系统角色固定：`owner / admin / project_admin / member / viewer / ai_agent`；权限点矩阵用后端代码常量维护（contracts 同步类型给前端）。
- 只建两张表，职责定死、**禁止双写同一用户的项目角色**：
  - `project_members`：用户是否属于项目 + 项目内基础角色（project_admin / member / viewer）。
  - `role_bindings`：tenant 级授权、AI Agent 授权、跨项目/特殊授权预留（`subject_type: user | ai_agent`，`scope_type: tenant | project`）。
- 权限校验唯一入口：`core/access.py` 的 `can(subject, action, scope)` + `require_permission` 依赖。
- 自定义角色/字段级权限时再经 Alembic 加三张表，把代码矩阵迁库（v0.9）。

### D4 AI 动作风险等级（3 级，四处枚举保持一致）

`read / low_write / high_write`，不引入 medium_write。MCP tag、AgentAction、SkillInvocation、AuditLog 共用。

- `read`：只读查询、总结、检索、生成分析 → 直接执行。
- `low_write`：创建工作项/Intake、评论、改负责人、状态流转、补充字段 → **默认需确认**；后续可由项目管理员配置部分动作自动执行。
- `high_write`：删除、权限变更、审批通过、导出敏感数据、改 Skill 凭证、改流程关键配置 → **v0.1 禁止 AI 执行**。

`AgentAction.status`：`pending / approved / rejected / executed / failed / expired`。

### D5 AI 身份穿透（delegation token 方案）

AI 代表用户调用 WorkNexus MCP 时，身份经 **WorkNexus 短期 delegation token** 传递，header：`X-WorkNexus-Delegation: wn_del_xxx`。MCP 请求**双 token 校验**：multirag server token（请求来源）+ delegation token（代表的用户）。

```text
用户在 WorkChat 发起请求
  → WorkNexus 生成短期 delegation token
  → 调 multirag agent completions（custom_header 携带）
  → multirag agent 调 WorkNexus /mcp（custom_header 自动透传）
  → WorkNexus 校验 server token + delegation token
  → 还原 represented_user / agent / project / conversation
  → 双重校验 → AgentAction / SkillInvocation / AuditLog
```

- 双重校验公式（写死）：用户权限 ∧ AI Agent 权限 ∧ 资源权限 ∧ 风险等级 ∧ 确认状态。
- delegation token：不透明随机串、DB 只存 hash（表 `mcp_delegation_tokens`，含 `permissions_snapshot` 签发时权限快照）、TTL 5–10 分钟、绑定 tenant/user/agent/project/conversation/run、日志脱敏、不进 SkillInvocation 明文 input、不写入 multirag 可见的 prompt 上下文。一次 agent run 内可多次使用（不强制 one-time）。
- **tool 参数不得作为认证依据**（可作业务字段）；custom_header 中禁止直接传 user_id / email / session token。

### D6 AI 上下文权限过滤（底层原则）

**用户看不到的数据，AI 也不能作为上下文读取。** AI 上下文构建必须先做权限过滤（项目、工作项、消息、知识引用全部过滤后才能进入 multirag 调用）。

### D7 multirag 对接方式（v0.1 接真实平台）

- WorkNexus → multirag：AI Adapter 调 `/api/v1/agents/{agent_id}/completions`（SSE），认证 `Authorization: Bearer <APIToken>`（multirag 侧鉴权粒度为 tenant）。
- multirag → WorkNexus：在 multirag 配置 MCPServer 指向 WorkNexus `/mcp`（streamable-http），server token 存其 `headers`；用户级身份走 D5 的 delegation token。
- WorkNexus 不信任 AI 平台的权限判断，落库前必须自行校验。
- AI 连接配置（endpoint、APIToken、默认 agent_id、MCP server token）**v0.1 以 .env 为准**，设置页只读脱敏展示；落库可配后置。
- Dashboard 的 AI 洞察允许 v0.1 先由规则生成，再切换 multirag。

### D8 数据与日志通用约定

- 所有核心业务表必有 `id / tenant_id / created_at / updated_at`（EntityMixin）；**重要业务表另加 `created_by / updated_by`**，软删除 `deleted_at` 按需。
- 后端统一 `request_id`：中间件注入、结构化日志携带、错误响应可追踪。
- API 路径一律 `/api/v1/*`；工作项类聚合资源采用"项目下创建/列表 + 平铺详情"的嵌套风格（见功能规格书）。

### D9 v0.1 明确不做（后置清单）

departments/组织树、完整动态 RBAC、SSO 实接、完整 IM、可视化流程设计器、AI 表格、完整审批流、Cycle/Sprint、Gantt/Roadmap、客户 CRM、自动化引擎、多租户 UI（数据已预留 tenant_id）、WebSocket 实时协作、完整文档知识库、移动端。入口与数据结构按版本路线（第 7 节）预留。

## 5. 各模块 v0.1 范围概述

> 字段、API、页面、验收标准级别的细节见 `docs/reference/v0.1-feature-spec.md` 对应章节；开发某模块前据此展开 `docs/modules/<module>.md`，有疑问先与用户讨论。

- **M1 identity**（规格书 §1）：表 tenants/users/sessions/invite_tokens/project_members/role_bindings/ai_agents/mcp_delegation_tokens/audit_logs；`/setup`、登录/登出、邀请（复制链接激活）、`/api/v1/me`（CurrentUserContext）、`core/access.py`、delegation token 签发与校验、审计写入函数；前端 login/setup 页 + AppShell 用户菜单。
- **M2 projects**（§2）：项目 CRUD/归档、成员管理、项目概览（含 AI 创建数等统计）；列表只返回有 `project.read` 的项目。
- **M3 work_items**（§3）：8 种类型、固定状态机（含 review 回退、任意非 done 可取消）、评论（Markdown）、活动日志、7 类关系、类型专属字段入 custom_fields(JSONB)；List + Board（拖拽可降级为状态按钮）；本模块 MCP tools（create/update/search/get/comment/transition，带风险 tag）。
- **M4 skills**（§4）：`/mcp` 双 token 校验中间件、skill_invocations 全量留痕（含 represented_user_id、agent_action_id、输入输出摘要不存敏感明文）、5 个 Skill（workitem/project/intake/report/knowledge，knowledge 代理 multirag）、Skills 中心页。
- **M5 workchat**（§5）：conversations/messages/agent_actions；AI Adapter（multirag SSE + delegation token + custom_header）；AI 返回三类（message / proposed_action / knowledge_result）；8 种 v0.1 动作；确认卡片 → 双重校验 → 执行 → 留痕全链路；项目 AI Chat 页 + AI Sidecar 容器预留。
- **M6 intake**（§6）：7 态请求池、4 来源（manual/ai_chat/api/mcp）、AI 摘要/分类/类型/优先级/负责人推荐、接受转工作项（保留 created_from_intake 关系）/拒绝/标记重复/稍后处理。
- **M7 dashboards**（§7）：固定项目仪表盘（状态/类型/优先级/负责人分布、逾期、AI 创建数、Intake 转化、近 7 天趋势）+ AI 洞察卡片（规则版起步可切 multirag）。
- **M8 settings/audit/home 完善**（§8/§9）：审计查询页（actor/resource/project/action 过滤）、Settings Lite（资料/项目/AI 连接脱敏展示/Skill 开关）、工作台 Home（我的待办/逾期/待确认 AI 动作/最近 AI 创建）。

## 6. 会话工作流（强制）

1. 读 `AGENTS.md` → 读本文件 → 读/建模块文档（底稿：`docs/reference/v0.1-feature-spec.md`）。
2. **有疑问必须先与用户讨论敲定**（范围、交互、字段、对接细节），不允许靠假设开发。
3. 开发遵守 AGENTS.md 全部规范（统一写法手册、i18n 双语、测试、PR 规范）。
4. PR 完成时：更新模块文档变更记录 + 更新本文件第 3 节进度 + 必要时在第 8 节追加变更。

## 7. 版本路线（v0.1 之后）

| 版本 | 主题 | 核心内容 |
| --- | --- | --- |
| v0.2 | 工作项增强 | 自定义字段、模板、批量编辑、附件、关注订阅、关系增强、保存视图/分组/高级筛选、站内通知 Lite、搜索 |
| v0.3 | 流程升级 | Workflow 配置（definitions/versions/states/transitions）、审批 Lite、自动化 Lite、AI 流程辅助 |
| v0.4 | Intake 完整化 | 公开/项目表单、API/Webhook/邮箱/IM 多渠道、AI 分流去重增强、Intake 统计 |
| v0.5 | AI 表格 / Data Apps | data_tables/fields/records/views、多视图、与工作项联动、自然语言建表 |
| v0.6 | Dashboard Builder | 可配置图表与布局、跨项目分析、AI 解释趋势/生成周报 |
| v0.7 | Docs / Knowledge / Meeting | 文档与版本、会议纪要转任务、AI 提取任务/验收标准；multirag 管 RAG，WorkNexus 管业务关联 |
| v0.8 | Cycle / Sprint / Roadmap | 迭代周期、燃尽、里程碑、AI 迭代计划 |
| v0.9 | 企业级权限与组织 | 动态 RBAC 迁库、字段级权限、departments 组织树、SSO（OIDC/SAML）、安全合规 |
| v1.0 | Agentic WorkOS | 数字分身/PM/QA 等 Agent 矩阵、AI 进流程节点、自动化平台（trigger/condition/action）、Skill 注册中心与凭证、外部集成生态 |

## 8. 大纲变更记录

| 日期 | 变更 | 确认人 |
| --- | --- | --- |
| 2026-06-12 | 初版：模块总览、M1–M8 顺序、D1–D8 决策（IAM 精简 RBAC、3 级风险、delegation token、departments 后置、接真实 multirag） | dxl |
| 2026-06-12 | 吸收 GPT-5.5 Pro v0.1 开发计划：新增功能规格书（docs/reference/v0.1-feature-spec.md）、M4 Skills 骨架提前到 WorkChat 前、AgentAction 增加 expired 态、新增 invite_tokens/mcp_delegation_tokens 表、D8 数据与日志约定、16 步验收链路、v0.2–v1.0 版本路线 | dxl |
| 2026-06-15 | M6 intake 设计敲定 A–H（规则版可替换 TriageEngine·建议性·带 provenance·不依赖 multirag；manual/ai_chat 真接、mcp 预留、api/email/IM 占位；单步 accept=接受并转换·原子；直接扩展 M5 dispatcher 不做 registry；来源用 source/ref id 表达不建 relation 行；3xxx + intake.* 审计 + 复用 intake.read/create/triage 权限；转化率归 M7、Home 归 M8），详见 docs/modules/intake.md | dxl |
| 2026-06-15 | M7 dashboard 设计敲定 A–H（规则版可替换 InsightsEngine 复刻 TriageEngine·按需算不缓存·带 provenance；领域 metrics read-model 归各自模块、dashboards 只编排不 import 他模块 models、M3 get_project_summary 重构复用同口径、aiCreatedCount 沿用 ai_chat+mcp 另加 sourceCounts、完成趋势取自 status_changed→done 活动；四端点 summary/workload/overdue 分页/ai-insights；仅项目级；read MCP 工具作独立 PR；无新错误码·读不审计·复用 dashboard.read；无新表/无迁移仅加 config flag），详见 docs/modules/dashboard.md | dxl |
