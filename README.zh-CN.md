# WorkNexus

<p align="center">
  <strong>把 AI 建议转成可治理团队工作的 AI-native WorkOS。</strong>
</p>

<p align="center">
  <a href="README.md">English</a>
  ·
  <a href="docs/roadmap.md">Roadmap</a>
  ·
  <a href="docs/reference/v0.1-feature-spec.md">v0.1 Spec</a>
  ·
  <a href="docs/tech-stack.md">Tech Stack</a>
</p>

<p align="center">
  <a href="docs/roadmap.md"><img alt="v0.1 status" src="https://img.shields.io/badge/v0.1-M6%20complete-4f46e5"></a>
  <img alt="React" src="https://img.shields.io/badge/React-19-149eca">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136-009688">
  <img alt="FastMCP" src="https://img.shields.io/badge/FastMCP-3.4-7c3aed">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-17-336791">
  <img alt="License" src="https://img.shields.io/badge/license-not%20declared-lightgrey">
</p>

WorkNexus（智协中枢）是一个面向 AI 协作团队的工作操作系统。它把项目、工作项、Intake、AI
WorkChat、Skills/MCP、权限与审计放进同一套业务数据底座。

它刻意**不做**模型编排平台。WorkNexus 与已有 AI 平台（`multirag`，默认
`http://localhost:8123`）并列协作：multirag 负责模型、RAG、智能体、工作流、MCP Client 与
Prompt；WorkNexus 负责业务数据、权限校验、人工确认、动作执行与审计。

> AI 可以提出动作。WorkNexus 负责校验权限、按风险要求让人确认、通过 service 层执行，并记录完整审计链路。

## 当前状态

WorkNexus 正处于 `v0.1` 活跃开发阶段。路线图已推进到 **M6 Intake**；仪表盘与最终的设置/审计/Home
完善仍未开始。

| 里程碑 | 范围                                     | 状态   |
| ------ | ---------------------------------------- | ------ |
| M0     | Monorepo 脚手架                          | 已完成 |
| M1     | 身份、权限、会话、邀请、delegation token | 已完成 |
| M2     | 项目空间与成员                           | 已完成 |
| M3     | 工作项、Workflow Lite、列表、抽屉、看板  | 已完成 |
| M4     | Skills/MCP 骨架与调用留痕                | 已完成 |
| M5     | AI WorkChat、SSE runs、AgentAction 确认  | 已完成 |
| M6     | Intake 收件箱、分诊、接受转工作项        | 已完成 |
| M7     | 项目仪表盘                               | 未开始 |
| M8     | 审计 UI、设置完善、Home 工作台           | 未开始 |

Roadmap 范围、关键决策与实现顺序以 [docs/roadmap.md](docs/roadmap.md) 为准。

## 现在可以体验

- 首启初始化、本地登录、HttpOnly Cookie 会话、邀请链接与成员管理。
- 项目创建、归档、项目详情、概览统计与项目成员角色。
- 工作项创建、编辑、评论、活动时间线、关系、状态流转与看板视图。
- WorkNexus `/mcp` 业务工具，采用 server token + 短期 delegation token。
- MCP 调用的 SkillInvocation 留痕，包括风险等级、代表用户与执行状态。
- 项目 AI WorkChat，支持流式响应、动作提案、批准/拒绝确认卡片。
- Intake 收件箱，支持规则版建议分诊、详情抽屉、重复/拒绝/稍后处理、原子接受转工作项。
- React 前端与 FastAPI 后端共享 OpenAPI 生成的 TypeScript contracts。

离线或确定性本地 AI 测试可设置 `WORKNEXUS_AI_CLIENT=fake`。真实 multirag adapter 已接入，但 live
endpoint/body 仍是 WorkChat 模块文档中跟踪的验证项。

## 为什么做 WorkNexus

多数 AI 工作工具停在聊天、检索或流程编排。WorkNexus 聚焦在真正落库执行的边界：

| 问题                              | WorkNexus 的回答                                                        |
| --------------------------------- | ----------------------------------------------------------------------- |
| AI 能建议工作，但业务数据散在别处 | 项目、工作项、Intake 与审计日志都是 WorkNexus 的一等系统记录            |
| AI 写动作有风险                   | 低风险写动作先变成 `AgentAction`，用户确认后才执行                      |
| 工具调用容易绕过权限              | WorkNexus 重新校验用户权限、AI Agent 权限、资源范围、风险等级与确认状态 |
| Agent 活动事后难解释              | Skill 调用、动作提案、用户确认、执行结果与审计日志互相关联              |
| AI 平台和业务系统边界容易混乱     | multirag 负责“想和调度”；WorkNexus 负责“校验、确认、执行、审计”         |

## AI 安全模型

WorkNexus 把模型输出与 MCP tool 调用都视为不可信输入。

- **AgentAction 确认流：** AI 生成的写动作先记录为 pending action；用户在 WorkNexus 内批准或拒绝。
- **MCP 双 token：** `/mcp` 同时要求 server token 与 `X-WorkNexus-Delegation`，后者是短期 token，
  绑定用户、agent、项目、conversation 与 run。
- **固定风险等级：** `read`、`low_write`、`high_write` 在 MCP tool、AgentAction、SkillInvocation
  与 AuditLog 中共用。
- **双重校验公式：** 执行必须同时满足用户权限 AND AI Agent 权限 AND 资源权限 AND 风险等级 AND
  确认状态。
- **service 层写库：** REST 路由与 MCP tools 保持薄暴露层；模块 service 是唯一写库边界，并在同一事务写审计。
- **AI 内容安全渲染：** 前端 AI/Markdown 内容统一走项目 Markdown wrapper，不直接使用
  `dangerouslySetInnerHTML`。

## 架构

```text
User / Browser
  -> apps/web                 React 19 + Vite + Tailwind CSS 4
  -> apps/server /api/v1      FastAPI REST API
  -> apps/server /mcp         FastMCP business tools
  -> PostgreSQL               system of record

WorkNexus -> multirag         通过 AI Adapter 调用模型 / RAG / 智能体编排
multirag  -> WorkNexus /mcp   携带 delegated user identity 调用业务工具
```

仓库结构：

```text
apps/
  web/             React 前端 workspace
  server/          FastAPI + FastMCP 后端，使用 uv 管理
packages/
  contracts/       orval 生成的 API 类型与 client
docs/
  modules/         模块设计文档与变更记录
  roadmap.md       产品范围、决策与进度
  tech-stack.md    技术栈定版与升级策略
infra/docker/      本地 PostgreSQL compose 栈
```

## 技术栈

| 层            | 技术                                                                                         |
| ------------- | -------------------------------------------------------------------------------------------- |
| 前端          | React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui, react-router, TanStack Query, zustand |
| 后端          | Python 3.13, FastAPI, FastMCP, Pydantic v2, SQLAlchemy 2 async, Alembic                      |
| 数据库        | PostgreSQL 17                                                                                |
| API contracts | OpenAPI + orval                                                                              |
| 质量工具      | ESLint, Prettier, Vitest, Playwright, ruff, mypy, pytest                                     |

精确版本与依赖规则见 [docs/tech-stack.md](docs/tech-stack.md)。

## 快速开始

### 前置要求

- Node.js `>=22.12`
- npm `>=10`
- Python `>=3.13`
- uv
- Docker，或另一个 PostgreSQL 17 兼容的本地数据库

### 安装

```bash
npm install
cd apps/server && uv sync
```

### 配置

使用仓库自带的 docker compose 数据库时，大多数本地默认配置可以直接工作。如需显式配置，可把共享示例复制到对应应用目录：

```bash
cp .env.example apps/server/.env
cp .env.example apps/web/.env
```

本地默认端口：

| 配置       | 默认值                                                              |
| ---------- | ------------------------------------------------------------------- |
| 前端       | `http://localhost:5173`                                             |
| REST API   | `http://localhost:8200/api/v1`                                      |
| MCP        | `http://localhost:8200/mcp`                                         |
| PostgreSQL | `postgresql+asyncpg://worknexus:worknexus@localhost:5432/worknexus` |
| AI 平台    | `http://localhost:8123`                                             |

没有本地 multirag 时，可在 `apps/server/.env` 设置：

```bash
WORKNEXUS_AI_CLIENT=fake
```

### 启动

```bash
# 1. 启动 PostgreSQL
cd infra/docker
docker compose up -d
cd ../..

# 2. 执行数据库迁移
cd apps/server
uv run alembic upgrade head
cd ../..

# 3. 启动后端
npm run dev:server
```

另开一个终端：

```bash
npm run dev:web
```

打开 `http://localhost:5173`。全新数据库需要先完成 `/setup` 首启初始化流程。

## 常用命令

| 命令                         | 说明                                              |
| ---------------------------- | ------------------------------------------------- |
| `npm run dev:web`            | 启动 Vite 前端                                    |
| `npm run build:web`          | 前端类型检查与构建                                |
| `npm run lint:web`           | 运行前端 lint                                     |
| `npm run test:web`           | 运行前端单测                                      |
| `npm run dev:server`         | 在 `8200` 端口启动 FastAPI + FastMCP              |
| `npm run test:server`        | 运行后端测试                                      |
| `npm run contracts:generate` | 刷新 OpenAPI JSON 并重新生成 `packages/contracts` |
| `npm run e2e`                | 运行 Playwright E2E 测试                          |

后端质量命令在 `apps/server` 目录运行：

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
```

## 开发契约

WorkNexus 使用文档驱动开发。每个实现会话都从以下文档开始：

1. [AGENTS.md](AGENTS.md)
2. [docs/roadmap.md](docs/roadmap.md)
3. 对应的 `docs/modules/<module>.md`

关键规则：

- 后端写库必须走模块 `service.py`；REST router 与 MCP tool 保持薄暴露层。
- REST 响应使用唯一 Envelope 结构：`{ "code": 0, "message": "ok", "data": ... }`。
- 前端请求走生成的 contracts 与 TanStack Query hooks。
- 前端用户可见文案必须走类型化 i18n，并同时提供 `zh-CN` 与 `en-US`。
- 主题颜色必须使用语义 Tailwind token，禁止裸色值类。
- AI 写动作必须走 AgentAction 确认流并记录审计。

完整工程规范见 [AGENTS.md](AGENTS.md)。`CLAUDE.md` 是同步镜像，任何修改 `AGENTS.md` 的提交都必须同步修改
`CLAUDE.md`。

## 文档

- [Roadmap](docs/roadmap.md)：`v0.1` 范围、模块顺序与固定决策。
- [技术栈](docs/tech-stack.md)：版本基线与升级规则。
- [开发流程](docs/development-workflow.md)：分支、PR 与模块开发流程。
- [功能规格](docs/reference/v0.1-feature-spec.md)：`v0.1` 详细验收范围。
- [模块文档](docs/modules)：各模块实现说明与变更记录。

## 贡献

本仓库当前遵循 [AGENTS.md](AGENTS.md) 与 [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)
中的项目本地贡献规则。

提交信息使用英文 Conventional Commits：

```text
feat(work-items): create work item board
fix(identity): expire revoked invite tokens
docs(skills): clarify MCP risk tags
```

## License

当前尚未声明开源许可证。在添加 `LICENSE` 文件之前，请将本仓库视为私有/内部项目。
