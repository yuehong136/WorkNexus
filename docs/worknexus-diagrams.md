# WorkNexus 图谱集

> 本文件按当前仓库状态绘制：M0-M6 已完成，M7/M8 未开始；技术栈以 `docs/tech-stack.md` 的 2026-06-12 定版为准。

## 1. 开发流程图

```mermaid
flowchart TD
  A["任务输入<br/>目标、模块、验收标准、特殊约束"] --> B["会话必读链<br/>AGENTS.md -> roadmap -> module doc"]
  B --> C{"模块文档是否存在"}
  C -- "不存在" --> D["从 _template.md 创建模块文档<br/>先写目标、边界、模型、API、MCP、UI、测试点"]
  C -- "已存在" --> E["读取模块文档<br/>确认历史决策与变更记录"]
  D --> F{"范围或设计是否有疑问"}
  E --> F
  F -- "有疑问" --> G["先与用户讨论敲定<br/>禁止靠假设开发"]
  F -- "无疑问" --> H["后端实现<br/>models -> migration -> schemas -> service -> router/mcp"]
  G --> H
  H --> I["后端验证<br/>ruff、mypy、pytest、alembic、REST/MCP 测试"]
  I --> J{"REST 契约是否变化"}
  J -- "是" --> K["npm run contracts:generate<br/>生成 packages/contracts"]
  J -- "否" --> L["前端实现"]
  K --> L["前端实现<br/>feature api hooks -> components -> routes -> i18n"]
  L --> M["前端验证<br/>lint、typecheck、vitest、build"]
  M --> N{"是否涉及主链路"}
  N -- "是" --> O["Playwright E2E<br/>覆盖用户可验证闭环"]
  N -- "否" --> P["轻量回归验证"]
  O --> Q["收口文档<br/>模块变更记录 + roadmap 进度"]
  P --> Q
  Q --> R["PR 自查<br/>一 PR 一意图、Conventional Commit、模板清单"]
```

## 2. 完整功能设计图

```mermaid
flowchart TB
  W["WorkNexus<br/>AI-native 团队协作与工单 WorkOS"]

  subgraph Foundation["基础底座"]
    M0["M0 脚手架<br/>已完成"]
    M1["M1 Identity & Access<br/>已完成<br/>setup、login、session、invite、RBAC、delegation、audit"]
  end

  subgraph CoreWork["核心工作管理"]
    M2["M2 项目空间<br/>已完成<br/>项目 CRUD、归档、成员管理、项目概览"]
    M3["M3 工作对象与看板<br/>已完成<br/>8 类型、Workflow Lite、评论、活动、关系、看板"]
    M6["M6 Intake 请求池<br/>已完成<br/>收件箱、规则分诊、拒绝、重复、稍后、接受转工作项"]
  end

  subgraph AIExecution["AI 参与工作流"]
    M4["M4 Skills / MCP<br/>已完成<br/>双 token、风险门禁、skill_invocations、/skills"]
    M5["M5 WorkChat + AgentAction<br/>已完成<br/>SSE、AI Adapter、提案、确认、执行、审计"]
  end

  subgraph Pending["待完成模块"]
    M7["M7 Dashboards<br/>未开始<br/>状态、类型、优先级、负责人、逾期、AI 创建、Intake 转化"]
    M8["M8 Settings / Audit / Home<br/>未开始<br/>审计查询、设置完善、我的待办、待确认动作"]
  end

  W --> Foundation
  W --> CoreWork
  W --> AIExecution
  W --> Pending

  M1 --> M2
  M2 --> M3
  M3 --> M4
  M4 --> M5
  M3 --> M6
  M5 --> M6
  M3 --> M7
  M6 --> M7
  M1 --> M8
  M5 --> M8
```

## 3. 系统架构图

```mermaid
flowchart LR
  User["用户 / Browser"] --> Web["apps/web<br/>React 19 + Vite + Tailwind 4"]
  Web -->|HTTP credentials include| REST["apps/server /api/v1<br/>FastAPI REST"]
  Web -->|POST SSE| Runs["/api/v1/workchat/runs<br/>WorkNexus SSE 事件"]

  subgraph Server["apps/server 模块化单体"]
    REST --> API["api.py<br/>REST 组合层"]
    Runs --> Workchat["workchat<br/>Conversation、Message、AgentAction、AI Adapter"]
    API --> Identity["identity<br/>User、Session、RoleBinding、Delegation"]
    API --> Projects["projects<br/>Project、Member"]
    API --> WorkItems["work_items<br/>WorkItem、Comment、Activity、Relation"]
    API --> Intake["intake<br/>IntakeRequest、TriageEngine"]
    API --> Skills["skills<br/>SkillInvocation、MCP middleware"]
    API --> Audit["audit<br/>AuditLog"]
    Skills --> MCP["/mcp<br/>FastMCP root server"]
    MCP --> WorkItemTools["workitem tools<br/>read / low_write"]
    MCP --> IntakeTools["intake tools<br/>read / low_write"]
  end

  Server --> DB[("PostgreSQL 17<br/>system of record")]

  Workchat -->|AI Adapter<br/>Bearer API token| Multirag["multirag<br/>模型、RAG、Agent、Workflow、MCP Client、Prompt"]
  Multirag -->|streamable-http<br/>Authorization Bearer + X-WorkNexus-Delegation| MCP

  MCP -->|read| WorkItems
  MCP -->|low_write| AgentAction["AgentAction pending<br/>用户确认后执行"]
  AgentAction --> Workchat
  Workchat -->|dispatcher 调 service| WorkItems
  Workchat -->|dispatcher 调 service| Intake
  Workchat --> Audit
  Skills --> Audit
```

## 4. AI 写动作安全链路图

```mermaid
sequenceDiagram
  autonumber
  participant U as 用户
  participant W as WorkNexus Web
  participant S as WorkNexus Server
  participant MR as multirag
  participant MCP as WorkNexus /mcp
  participant DB as PostgreSQL

  U->>W: 在项目 AI Chat 发消息
  W->>S: POST /workchat/runs
  S->>DB: 读取项目、会话、可见工作项
  S->>S: D6 权限过滤上下文
  S->>DB: 签发短期 delegation token
  S->>MR: 调 agent completions<br/>custom_header 带 delegation
  MR->>MCP: 调 WorkNexus low_write tool
  MCP->>S: 双 token 校验 + 风险识别
  S->>DB: 写 SkillInvocation
  S->>DB: 创建 AgentAction pending
  S-->>MR: 返回 pending_confirmation
  MR-->>S: SSE 文本与 tool_result
  S-->>W: agent_action 事件
  W-->>U: 展示 AgentActionCard
  U->>W: 批准动作
  W->>S: POST /agent-actions/{id}/approve
  S->>S: 实时双重校验<br/>用户权限 AND Agent 权限 AND 资源权限 AND 风险等级 AND 确认状态
  S->>DB: service 层执行业务写入
  S->>DB: 写 audit_logs 并更新 AgentAction executed
  S-->>W: 返回执行结果
```

## 5. 技术栈分层图

```mermaid
flowchart TB
  subgraph Frontend["前端 apps/web"]
    FE1["React 19.2.7"]
    FE2["TypeScript 6.0.3"]
    FE3["Vite 8.0.16"]
    FE4["Tailwind CSS 4.3.0<br/>CSS-first @theme"]
    FE5["shadcn/ui + Radix<br/>lucide-react"]
    FE6["react-router 7.17.0"]
    FE7["TanStack Query 5.101.0<br/>zustand 5.0.14"]
    FE8["react-hook-form 7.x<br/>zod 4.4.3"]
    FE9["i18next 26.3.1<br/>react-i18next 17.0.8"]
    FE10["vitest 4.1.8<br/>Testing Library / Playwright 1.60.0 / msw 2.14.6"]
  end

  subgraph Contracts["契约 packages/contracts"]
    CT1["OpenAPI"]
    CT2["orval 8.17.0"]
    CT3["自定义 fetch mutator<br/>credentials include + Envelope unwrap"]
  end

  subgraph Backend["后端 apps/server"]
    BE1["Python 3.13.x"]
    BE2["FastAPI 0.136.3<br/>Uvicorn 0.49.0"]
    BE3["FastMCP 3.4.2<br/>mount + namespace + middleware"]
    BE4["Pydantic v2<br/>pydantic-settings 2.14.1"]
    BE5["SQLAlchemy 2.0.50 async<br/>asyncpg"]
    BE6["Alembic 1.18.4"]
    BE7["ruff 0.15.x<br/>mypy strict<br/>pytest 9.0.3"]
  end

  subgraph Data["数据与外部系统"]
    DB["PostgreSQL 17"]
    AI["multirag<br/>现有 AI 平台"]
  end

  FE7 --> CT3
  CT1 --> CT2 --> CT3
  CT3 --> BE2
  BE2 --> BE4
  BE2 --> BE3
  BE2 --> BE5
  BE5 --> DB
  BE3 --> AI
  AI --> BE3
```

## 6. 数据域关系图

```mermaid
erDiagram
  TENANTS ||--o{ USERS : owns
  TENANTS ||--o{ PROJECTS : owns
  USERS ||--o{ SESSIONS : has
  USERS ||--o{ INVITE_TOKENS : creates
  USERS ||--o{ PROJECT_MEMBERS : joins
  PROJECTS ||--o{ PROJECT_MEMBERS : has
  ROLE_BINDINGS }o--|| TENANTS : scopes
  AI_AGENTS ||--o{ MCP_DELEGATION_TOKENS : receives
  USERS ||--o{ MCP_DELEGATION_TOKENS : represented_by

  PROJECTS ||--o{ WORK_ITEMS : contains
  WORK_ITEMS ||--o{ WORK_ITEM_COMMENTS : has
  WORK_ITEMS ||--o{ WORK_ITEM_ACTIVITIES : records
  WORK_ITEMS ||--o{ WORK_ITEM_RELATIONS : source

  PROJECTS ||--o{ CONVERSATIONS : has
  CONVERSATIONS ||--o{ MESSAGES : has
  CONVERSATIONS ||--o{ AGENT_ACTIONS : proposes
  AI_AGENTS ||--o{ AGENT_ACTIONS : requests

  PROJECTS ||--o{ INTAKE_REQUESTS : receives
  INTAKE_REQUESTS ||--o| WORK_ITEMS : converts_to

  AI_AGENTS ||--o{ SKILL_INVOCATIONS : calls
  USERS ||--o{ SKILL_INVOCATIONS : represented_user
  SKILL_INVOCATIONS ||--o| AGENT_ACTIONS : creates

  TENANTS ||--o{ AUDIT_LOGS : records
```

## 7. 模块依赖与实施顺序图

```mermaid
flowchart LR
  M0["M0 Scaffold<br/>运行骨架"] --> M1["M1 Identity & Access<br/>身份、权限、审计、delegation"]
  M1 --> M2["M2 Projects<br/>项目空间"]
  M2 --> M3["M3 Work Items<br/>工作对象、Workflow Lite、看板"]
  M3 --> M4["M4 Skills / MCP<br/>双 token、调用留痕"]
  M4 --> M5["M5 WorkChat + AgentAction<br/>AI 对话、提案、确认、执行"]
  M3 --> M6["M6 Intake<br/>请求池、分诊、转工作项"]
  M5 --> M6
  M3 --> M7["M7 Dashboards<br/>未开始"]
  M6 --> M7
  M1 --> M8["M8 Settings / Audit / Home<br/>未开始"]
  M5 --> M8
```
