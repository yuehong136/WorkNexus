# WorkNexus

<p align="center">
  <strong>面向受控团队执行的 AI-native WorkOS。</strong>
</p>

<p align="center">
  把 AI 建议转成经过权限校验、人工确认、完整审计的真实工作。
</p>

<p align="center">
  <a href="README.md">English</a>
  ·
  <a href="docs/roadmap.md">Roadmap</a>
  ·
  <a href="docs/reference/v0.1-feature-spec.md">v0.1 Spec</a>
  ·
  <a href="docs/tech-stack.md">Tech Stack</a>
  ·
  <a href="docs/development-workflow.md">Development</a>
</p>

<p align="center">
  <a href="docs/roadmap.md"><img alt="v0.1 status" src="https://img.shields.io/badge/v0.1-complete-22c55e"></a>
  <img alt="React" src="https://img.shields.io/badge/React-19-149eca">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136-009688">
  <img alt="FastMCP" src="https://img.shields.io/badge/FastMCP-3.4-7c3aed">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-17-336791">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue">
</p>

WorkNexus（智协中枢）是一个 AI-native 团队协作与工单 WorkOS。它把项目、工作对象、Intake、
AI WorkChat、Skills/MCP、仪表盘、权限与审计统一到同一套业务数据底座中。

WorkNexus **不是**模型编排平台。它与已有 AI 平台（`multirag`）并行：multirag 负责模型、RAG、
智能体、工作流、MCP Client 与 Prompt；WorkNexus 负责业务数据、权限校验、人工确认、执行落库与审计。

> AI 可以提出动作。WorkNexus 负责判断动作是否允许、必要时让人确认、通过 service 层执行，并记录完整链路。

## 为什么做 WorkNexus

很多 AI 工作工具停在聊天、检索或流程编排层。WorkNexus 关注的是 AI 输出真正变成业务状态的执行边界。

| 问题                              | WorkNexus 的回答                                                    |
| --------------------------------- | ------------------------------------------------------------------- |
| AI 提了建议，但业务记录分散在别处 | 项目、工作项、Intake、AgentAction、审计都是一等数据                 |
| 工具调用可能绕过产品权限          | 执行前重新校验用户权限、AI Agent 权限、资源范围、风险等级与确认状态 |
| AI 写动作天然有风险               | 低风险写动作先落为 pending `AgentAction`，由用户批准或拒绝          |
| Agent 行为事后难解释              | Skill 调用、提案、批准、执行结果与审计日志相互关联                  |
| AI 平台和业务系统边界容易混乱     | multirag 负责想和调度；WorkNexus 负责数据、权限、确认、执行、审计   |

## v0.1 状态

`v0.1` 已完成。主验收闭环已经端到端打通：

```text
/setup -> 登录 -> 项目 -> 工作项 -> 看板流转 -> AI WorkChat
  -> proposed AgentAction -> 用户批准 -> 落库
  -> skill_invocations -> audit_logs -> 仪表盘与工作台更新
```

最新 roadmap 记录了 M8 完成态，以及后端、前端、Playwright E2E 覆盖情况。
[docs/roadmap.md](docs/roadmap.md) 是范围与进度真相源。

| 里程碑 | 范围                                         | v0.1 |
| ------ | -------------------------------------------- | ---- |
| M0     | monorepo 脚手架                              | 完成 |
| M1     | Identity、会话、RBAC、邀请、delegation token | 完成 |
| M2     | 项目与成员                                   | 完成 |
| M3     | 工作项、Workflow Lite、评论、关系、看板      | 完成 |
| M4     | Skills/MCP 基础与调用留痕                    | 完成 |
| M5     | AI WorkChat、SSE run、AgentAction 确认       | 完成 |
| M6     | Intake 收件箱、分诊、接受转工作项            | 完成 |
| M7     | 项目仪表盘与规则版 AI 洞察                   | 完成 |
| M8     | 审计 UI、Settings Lite、Home 工作台          | 完成 |

## 核心能力

- **项目 WorkOS：**项目空间、项目成员、角色权限、项目概览与归档。
- **工作对象：**task、requirement、bug、risk、decision、approval、incident、feedback 八类记录，包含固定状态机、评论、活动、关系、custom fields、列表、详情抽屉与看板。
- **Intake：**请求池、规则版分诊建议、详情抽屉、标记重复/拒绝/稍后处理，以及原子化接受并转换为工作项。
- **AI WorkChat：**项目级会话、SSE 流式 run、proposed action、批准/拒绝卡片，以及适合本地开发的 fake AI 模式。
- **Skills/MCP：**FastMCP 业务工具、read/low_write 风险标签、双 token 访问、delegation 上下文、全量 SkillInvocation 留痕。
- **仪表盘：**状态/类型/优先级/来源分布、负责人负载、逾期、7 天趋势、Intake 转化率、规则版 AI 洞察。
- **审计与工作台：**tenant 级审计搜索、AI 链路下钻、脱敏 AI 连接设置、跨项目待办/逾期/待确认 AI 动作/最近 AI 创建/待处理 Intake。
- **契约优先前端：**OpenAPI 生成 TypeScript client、TanStack Query hooks、类型化 i18n、Tailwind 4 语义 token、shadcn/Radix 轻组件层。

## AI 安全模型

WorkNexus 把模型输出和 MCP 工具调用都视为不可信输入。

- **AgentAction 确认流：**AI 写动作先持久化为 pending action，由用户在 WorkNexus 中批准或拒绝。
- **MCP 双 token：**`/mcp` 同时要求 server bearer token 与 `X-WorkNexus-Delegation`，后者是短期用户代理 token，绑定 tenant/user/agent/project/conversation/run。
- **固定风险等级：**`read`、`low_write`、`high_write` 在 MCP tools、AgentAction、SkillInvocation、AuditLog 中共用。
- **执行公式：**用户权限 AND AI Agent 权限 AND 资源权限 AND 风险等级 AND 有效确认状态。
- **service 层写库：**REST router 与 MCP tool 保持薄层，领域 service 是写库边界，并在同事务内写审计。
- **AI 内容安全渲染：**AI/Markdown 内容统一经过项目 Markdown wrapper 与 DOMPurify，禁止裸 `dangerouslySetInnerHTML`。

## 架构

```text
Browser
  -> apps/web                  React 19 + Vite + Tailwind CSS 4
  -> apps/server /api/v1       FastAPI REST API
  -> apps/server /mcp          FastMCP business tools
  -> PostgreSQL                system of record

WorkNexus -> multirag          通过 AI Adapter 调模型 / RAG / Agent 编排
multirag  -> WorkNexus /mcp    带 delegation user identity 调业务工具
```

仓库结构：

```text
apps/
  web/                         React 前端 workspace
  server/                      uv 管理的 FastAPI + FastMCP 后端
packages/
  contracts/                   orval 生成的 API 类型与 client
docs/
  modules/                     模块设计文档与变更记录
  roadmap.md                   产品范围、决策与进度
  tech-stack.md                技术栈定版与升级策略
infra/docker/                  本地 PostgreSQL compose 栈
```

## 技术栈

| 层     | 技术                                                                                         |
| ------ | -------------------------------------------------------------------------------------------- |
| 前端   | React 19、TypeScript、Vite、Tailwind CSS 4、shadcn/ui、react-router、TanStack Query、zustand |
| 后端   | Python 3.13、FastAPI、FastMCP、Pydantic v2、SQLAlchemy 2 async、Alembic                      |
| 数据库 | PostgreSQL 17                                                                                |
| 契约   | OpenAPI + orval                                                                              |
| 质量   | ESLint、Prettier、Vitest、Playwright、ruff、mypy、pytest                                     |

精确版本与依赖规则见 [docs/tech-stack.md](docs/tech-stack.md)。

## 快速开始

### 前置条件

- Node.js `>=22.12`
- npm `>=10`
- Python `>=3.13`
- uv
- Docker，或其他 PostgreSQL 17 兼容实例

### 1. 安装依赖

```bash
npm install
cd apps/server && uv sync
cd ../..
```

### 2. 配置本地环境

```bash
cp .env.example apps/server/.env
printf 'VITE_API_BASE_URL=http://localhost:8200/api/v1\n' > apps/web/.env
```

如果本地没有可用的 multirag 实例，在 `apps/server/.env` 中使用 fake AI：

```bash
WORKNEXUS_AI_CLIENT=fake
```

使用真实 multirag adapter 前，请把 `apps/server/.env` 中的 AI 平台地址、API Key、默认外部 agent id 与 MCP server token 替换为当前环境值。

### 3. 启动 PostgreSQL 并迁移

```bash
cd infra/docker
docker compose up -d
cd ../..

cd apps/server
uv run alembic upgrade head
cd ../..
```

### 4. 启动应用

```bash
npm run dev:server
```

另开一个终端：

```bash
npm run dev:web
```

打开 `http://localhost:5173`。新数据库第一次进入时先完成 `/setup`。

## 常用命令

| 命令                         | 说明                                          |
| ---------------------------- | --------------------------------------------- |
| `npm run dev:web`            | 启动 Vite 前端                                |
| `npm run build:web`          | 前端类型检查与构建                            |
| `npm run lint:web`           | 前端 lint                                     |
| `npm run test:web`           | 前端单测                                      |
| `npm run dev:server`         | 在 `8200` 启动 FastAPI + FastMCP              |
| `npm run test:server`        | 后端测试                                      |
| `npm run contracts:generate` | 刷新 OpenAPI JSON 并生成 `packages/contracts` |
| `npm run e2e`                | 使用隔离数据库运行 Playwright E2E             |

后端质量命令在 `apps/server` 下运行：

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
```

## 文档

- [Roadmap](docs/roadmap.md)：v0.1 范围、模块顺序、固定决策与进度。
- [功能规格](docs/reference/v0.1-feature-spec.md)：v0.1 详细验收范围。
- [技术栈](docs/tech-stack.md)：版本基线与升级策略。
- [开发流程](docs/development-workflow.md)：分支、PR 与模块流程。
- [模块文档](docs/modules)：各模块实现说明与变更记录。
- [工程规范](AGENTS.md)：人类与 AI 贡献者必须遵守的仓库规则。

## 开发契约

每个实现会话按顺序阅读：

1. [AGENTS.md](AGENTS.md)
2. [docs/roadmap.md](docs/roadmap.md)
3. 相关 `docs/modules/<module>.md`

核心规则：

- 后端写库只经过模块 `service.py`，REST router 与 MCP tool 保持薄层。
- REST 响应只使用统一 Envelope：`{ "code": 0, "message": "ok", "data": ... }`。
- 前端请求经生成 contracts 与 TanStack Query hooks。
- 用户可见前端文案必须有 `zh-CN` 与 `en-US` 类型化 i18n 资源。
- 主题样式使用语义 Tailwind token，禁止裸色值类。
- AI 写动作必须经过 AgentAction 确认和审计。

`CLAUDE.md` 是 `AGENTS.md` 的同步镜像；修改 `AGENTS.md` 时必须同提交同步它。

## Roadmap

v0.1 已交付受控 AI 工作闭环。后续主题包括工作项增强、可配置 Workflow、更多 Intake 渠道、
AI 表格/Data Apps、Dashboard Builder、Docs/Knowledge/Meeting、Cycle/Roadmap、企业权限，以及更完整的
Agentic WorkOS。

完整 v0.2-v1.0 路线见 [docs/roadmap.md](docs/roadmap.md)。

## 贡献

本仓库遵循 [AGENTS.md](AGENTS.md) 与 [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)
中的项目规则。

Commit message 使用英文 Conventional Commits：

```text
feat(work-items): create work item board
fix(identity): expire revoked invite tokens
docs(skills): clarify MCP risk tags
```

## License

WorkNexus 采用 [Apache License 2.0](LICENSE)，与 RAGFlow 使用的开源协议类型保持一致。
