# WorkNexus 开发大纲（Roadmap）

> **本文件是每个开发会话的导航与共识文件。**
> 每次开发（人类或 AI 代理）必须按以下顺序进入工作：
> 1. 读 `AGENTS.md`（工程规范）
> 2. 读本文件（全局蓝图 + 当前进度 + 已敲定决策）
> 3. 读或创建对应的 `docs/modules/<module>.md`
> 4. **对范围、设计、细节有任何疑问，先与用户讨论敲定，再动手开发**
> 5. 开发完成后在同一 PR 内更新模块文档与本文件的进度/变更记录
>
> 本文件只记录"做什么、边界、已敲定的决策"，不写实现细节（实现细节在各模块文档）。
> 大纲本身的变更（范围、顺序、决策）必须经用户确认。

---

## 1. 产品定位

WorkNexus（智协中枢）：AI-native 团队协作与工单 WorkOS。让所有团队工作可见、可流转、可协同、可追踪、可被 AI 理解和推进。

边界（详见 AGENTS.md 第 1 节）：已有 AI 平台（multirag）负责"想和调度"（模型、知识库、智能体编排、MCP Client）；WorkNexus 负责"数据、权限、确认、执行、审计"，并通过 `/mcp` 把业务能力暴露给 AI 平台。

## 2. v0.1 目标闭环（验收标准）

```text
setup 初始化 → 登录 → 创建项目 → 创建工作项
  → AI WorkChat 生成工作项（真实 multirag）
  → 进入 Intake 或直接生成 AgentAction
  → 用户确认 AI 动作 → 落库
  → 列表 / 看板状态流转 → 活动日志
  → 仪表盘统计变化 → Skill 调用日志可追踪 → 审计日志可查询
```

闭环全链路打通 + Playwright E2E 覆盖，即 v0.1 完成。

## 3. 模块总览与进度

| # | 模块 | 后端 module | 前端 feature | 状态 | 模块文档 |
| --- | --- | --- | --- | --- | --- |
| M0 | 脚手架 | `worknexus` 骨架 | `app/` 骨架 | **已完成** | [scaffold.md](modules/scaffold.md) |
| M1 | Identity & Access | `identity`（+ `audit` 起步） | `auth`、`settings/members` | 未开始 | 待建 identity.md |
| M2 | 项目空间 | `projects` | `projects` | 未开始 | 待建 |
| M3 | 工作对象 | `work_items` | `work-items`、`board` | 未开始 | 待建 |
| M4 | AI WorkChat | `workchat`（含 agent_actions、AI Adapter） | `workchat` | 未开始 | 待建 |
| M5 | Intake | `intake` | `intake` | 未开始 | 待建 |
| M6 | Skills / MCP 中心 | `skills` | `skills` | 未开始 | 待建 |
| M7 | 仪表盘 | `dashboards` | `dashboard` | 未开始 | 待建 |
| M8 | 设置与审计 UI | `audit` 完善 | `settings`、`audit`、`home` 完善 | 未开始 | 待建 |

依赖关系：M1 是所有模块的前置（身份、权限、审计、AI Agent 身份）；M3 依赖 M2；M4 依赖 M3；M5 依赖 M3/M4；M6/M7 依赖 M3/M4 产生的数据。

## 4. 已敲定的关键决策（开发前必读）

### D1 技术栈与工程规范

见 `AGENTS.md`（版本定版、目录分层、统一写法手册、PR 规范）。提交信息一律英文。

### D2 认证与会话（v0.1）

- 本地账号（邮箱+密码，bcrypt）+ 邀请制（v0.1 复制邀请链接，不接邮件）+ `/setup` 首启初始化（建 owner、default tenant、种子角色、默认项目、默认 AI Agent，完成后封禁）。
- **Server-side session + HttpOnly Cookie**（Secure[prod]、SameSite=Lax、7 天、DB 只存 token hash）。禁止把会话 token 放 localStorage。前端 fetch 一律 `credentials: 'include'`。
- SSO/OIDC 不做但预留：`users.identity_provider`（`local | multirag | oidc`）+ `users.external_user_id`（映射 multirag 用户，32 hex）。
- 登录后 `GET /api/v1/me` 返回 `CurrentUserContext`（user + tenant + roles + permissions + 项目级权限），前端只据此控制菜单/按钮，**不自己推导权限**；后端永远强制校验。

### D3 权限模型（精简 RBAC，v0.1）

- **不建** roles / permissions / role_permissions 表。6 个系统角色固定：`owner / admin / project_admin / member / viewer / ai_agent`；权限点矩阵用后端代码常量维护（contracts 同步类型给前端）。
- 只建两张表，职责定死、**禁止双写同一用户的项目角色**：
  - `project_members`：用户是否属于项目 + 项目内基础角色（project_admin / member / viewer）。
  - `role_bindings`：tenant 级授权、AI Agent 授权、跨项目/特殊授权预留（`subject_type: user | ai_agent`，`scope_type: tenant | project`）。
- 权限校验唯一入口：`core/access.py` 的 `can(subject, action, scope)` + `require_permission` 依赖。
- 自定义角色/字段级权限时再经 Alembic 加三张表，把代码矩阵迁库（v0.2+）。

### D4 AI 动作风险等级（3 级，四处枚举保持一致）

`read / low_write / high_write`，不引入 medium_write。MCP tag、AgentAction、SkillInvocation、AuditLog 共用。

- `read`：只读查询、总结、检索、生成分析 → 直接执行。
- `low_write`：创建工作项/Intake、评论、改负责人、状态流转、补充字段 → **默认需确认**；后续可由项目管理员配置部分动作自动执行。
- `high_write`：删除、权限变更、审批通过、导出敏感数据、改 Skill 凭证、改流程关键配置 → **v0.1 禁止 AI 执行**。

### D5 AI 身份穿透（delegation token 方案）

AI 代表用户调用 WorkNexus MCP 时，身份经 **WorkNexus 短期 delegation token** 传递，header：`X-WorkNexus-Delegation: wn_del_xxx`。

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
- delegation token：不透明随机串、DB 只存 hash、TTL 5–10 分钟、绑定 tenant/user/agent/project/conversation/run、日志脱敏、不进 SkillInvocation 明文 input、不写入 multirag 可见的 prompt 上下文。一次 agent run 内可多次使用（不强制 one-time）。
- **tool 参数不得作为认证依据**（可作业务字段）；custom_header 中禁止直接传 user_id / email / session token。

### D6 AI 上下文权限过滤（底层原则）

**用户看不到的数据，AI 也不能作为上下文读取。** AI 上下文构建必须先做权限过滤。

### D7 multirag 对接方式（v0.1 接真实平台）

- WorkNexus → multirag：AI Adapter 调 `/api/v1/agents/{agent_id}/completions`（SSE），认证 `Authorization: Bearer <APIToken>`（multirag 侧鉴权粒度为 tenant）。
- multirag → WorkNexus：在 multirag 配置 MCPServer 指向 WorkNexus `/mcp`（streamable-http），server token 存其 `headers`；用户级身份走 D5 的 delegation token。
- WorkNexus 不信任 AI 平台的权限判断，落库前必须自行校验。

### D8 v0.1 明确不做（后置清单）

departments/组织树（v0.2+）、完整动态 RBAC、SSO 实接、完整 IM、可视化流程设计器、AI 表格（Data Table Lite 视进度）、完整审批流、Cycle/Sprint、Gantt/Timeline、客户管理（用 Feedback 工作项承载）、自动化引擎、多租户 UI（数据已预留 tenant_id）、WebSocket（先请求刷新）、移动端。

## 5. 各模块 v0.1 范围概述

> 开发某模块前，把本节对应条目展开成 `docs/modules/<module>.md`，有疑问先与用户讨论。

- **M1 identity**：表 tenants / users / sessions / role_bindings / ai_agents / audit_logs；`/setup`、登录/登出、邀请（复制链接）、`/api/v1/me`、`core/access.py` 权限校验、delegation token 签发与校验、审计写入函数；前端 login/setup 页 + AppShell 用户菜单。
- **M2 projects**：项目 CRUD、成员管理（project_members）、项目概览；项目列表只返回有 `project.read` 的项目；MCP：project 上下文查询 tools（read）。
- **M3 work_items**：8 种类型（task/requirement/bug/risk/decision/approval/incident/feedback）、Workflow Lite 状态机（backlog→todo→in_progress→review→done/cancelled）、评论、活动日志、关系（父子/阻塞/重复/相关）、类型专属字段（JSONB custom_fields）；List 视图（筛选/排序/搜索）+ Board 看板（拖拽流转）；MCP：workitem create/update/search/get/comment/transition tools（含风险 tag）。
- **M4 workchat**：conversations / messages / agent_actions 表；AI Adapter（multirag SSE + delegation token）；AI 建议卡片（Proposed Action → 确认/拒绝 → 执行落库）；项目级 AI Chat 页 + 页面 AI Sidecar 入口。
- **M5 intake**：intake_requests 表（7 态：new/triaging/accepted/rejected/duplicate/snoozed/converted）；来源 ai_chat/form/api；AI 摘要与分类（经 multirag）；接受转工作项/拒绝/标记重复；MCP：intake tools。
- **M6 skills**：skills / skill_tools 注册表（与 MCP 组合层同步）、skill_invocations 全量调用日志（输入输出摘要、风险等级、是否经确认、关联 audit）；Skills 中心页（列表/Tools/调用日志）。
- **M7 dashboards**：统计聚合（状态/类型/负责人分布、逾期、AI 创建数、Intake 转化）+ AI 洞察卡片（经 multirag）；recharts 图表（颜色取 CSS 变量）。
- **M8 settings/audit/home 完善**：审计日志查询页（操作人/类型/资源/前后变化/来源过滤）、项目与系统设置页、工作台 Home（我的待办/逾期/待确认 AI 动作/最近 AI 创建）。

## 6. 会话工作流（强制）

1. 读 `AGENTS.md` → 读本文件 → 读/建模块文档。
2. **有疑问必须先与用户讨论敲定**（范围、交互、字段、对接细节），不允许靠假设开发。
3. 开发遵守 AGENTS.md 全部规范（统一写法手册、i18n 双语、测试、PR 规范）。
4. PR 完成时：更新模块文档变更记录 + 更新本文件第 3 节进度 + 必要时在第 8 节追加变更。

## 7. v0.1 之后的方向（占位，按需展开）

Intake 多来源（邮箱/IM/Webhook）、工作项模板与自定义字段深化、通知中心、轻量自动化、Data Table Lite、文档/知识引用、Cycle 雏形、可视化流程、动态 RBAC、SSO、多租户、数字分身。

## 8. 大纲变更记录

| 日期 | 变更 | 确认人 |
| --- | --- | --- |
| 2026-06-12 | 初版：模块总览、M1–M8 顺序、D1–D8 决策（IAM 精简 RBAC、3 级风险、delegation token、departments 后置、接真实 multirag） | dxl |
