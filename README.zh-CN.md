# WorkNexus

[English](README.md) | [简体中文](README.zh-CN.md)

WorkNexus（智协中枢）是一个面向团队协作、工作项、Intake、AI WorkChat、Skills/MCP、权限与审计的 AI-native WorkOS。

它不是另一个模型编排平台。WorkNexus 负责业务数据、权限校验、人工确认、动作执行与审计记录；已有 AI 平台（`multirag`，默认 `http://localhost:8123`）负责模型、RAG、智能体编排、工作流编排、MCP Client 与 Prompt。

> AI 可以提出动作。WorkNexus 负责校验权限、按风险要求让人确认、通过 service 层执行，并记录完整审计链路。

## 项目状态

WorkNexus 正处于 `v0.1` 活跃开发阶段。

| 范围                                                        | 状态          |
| ----------------------------------------------------------- | ------------- |
| Monorepo 脚手架                                             | 已完成        |
| 身份、会话、权限控制、邀请、delegation token 基础能力       | 已完成        |
| 项目、工作项、Skills/MCP、WorkChat、Intake、仪表盘、审计 UI | `v0.1` 规划中 |

Roadmap 范围与实现顺序以 [docs/roadmap.md](docs/roadmap.md) 为准。

## 核心特性

- 面向 AI 辅助执行设计的项目与工作项数据模型，而不是只做聊天界面。
- Server-side session + HttpOnly Cookie，浏览器存储中不保存会话 token。
- 固定 RBAC 基线，支持租户级与项目级权限范围。
- WorkNexus 暴露 MCP 业务工具，采用 server token + 短期 delegation token。
- AI 生成写动作走 AgentAction 确认流。
- 工作项变更、AI 建议、用户确认、Skill 调用、权限变更、敏感操作等要求全量审计。
- 前端通过 OpenAPI 生成 TypeScript contracts，与后端接口保持一致。

## 架构

```text
User / Browser
  -> apps/web                 React 19 + Vite + Tailwind 4
  -> apps/server /api/v1      FastAPI REST API
  -> apps/server /mcp         FastMCP business tools
  -> PostgreSQL               system of record

WorkNexus -> multirag         调用模型 / RAG / 智能体编排
multirag  -> WorkNexus /mcp   携带用户 delegation identity 调用 MCP tools
```

仓库结构：

```text
apps/
  web/             React 前端 workspace
  server/          FastAPI + FastMCP 后端，使用 uv 管理
packages/
  contracts/       orval 生成的 API 类型与 client
docs/
  modules/         模块设计文档
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

精确版本与升级策略见 [docs/tech-stack.md](docs/tech-stack.md)。

## 快速开始

### 前置要求

- Node.js `>=22.12`
- npm `>=10`
- Python `>=3.13`
- uv
- Docker，或另一个 PostgreSQL 17 兼容的本地数据库

### 安装依赖

```bash
npm install
cd apps/server && uv sync
```

### 配置环境变量

使用仓库自带的 docker compose 数据库时，大多数本地默认配置可以直接工作。

如需显式配置，可把示例文件复制到对应应用目录：

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

### 本地启动

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

## 常用脚本

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

## 开发规范

WorkNexus 使用文档驱动开发。每个开发会话都从以下文档开始：

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

完整工程规范见 [AGENTS.md](AGENTS.md)。`CLAUDE.md` 是同步镜像，任何修改 `AGENTS.md` 的提交都必须同步修改 `CLAUDE.md`。

## 文档

- [Roadmap](docs/roadmap.md)：`v0.1` 范围、模块顺序与固定决策。
- [技术栈](docs/tech-stack.md)：版本基线与升级规则。
- [开发流程](docs/development-workflow.md)：分支、PR 与模块开发流程。
- [功能规格](docs/reference/v0.1-feature-spec.md)：`v0.1` 详细验收范围。
- [模块文档](docs/modules)：各模块实现说明与变更记录。

## 贡献

本仓库当前遵循 [AGENTS.md](AGENTS.md) 与 [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) 中的项目本地贡献规则。

提交信息使用英文 Conventional Commits：

```text
feat(work-items): create work item board
fix(identity): expire revoked invite tokens
docs(skills): clarify MCP risk tags
```

## License

当前尚未声明开源许可证。在添加 LICENSE 文件之前，请将本仓库视为私有/内部项目。
