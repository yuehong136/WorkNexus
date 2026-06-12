# WorkNexus（智协中枢）

WorkNexus 是一个 AI-native 团队协作与工单 WorkOS。
它以项目、工作对象、流程、Intake、AI WorkChat、Skills/MCP 和审计为核心，
把人的协作、AI 的建议、系统的执行统一到同一套工作数据底座中。

> WorkNexus：让团队工作被 AI 理解、被流程推进、被系统追踪。

## 与已有 AI 平台的关系

WorkNexus 不是第二个 AI 平台。已有 AI 平台（multirag）负责模型、知识库、智能体编排与 MCP 调度（"想和调度"）；WorkNexus 负责业务数据、权限、动作确认、执行与审计（"落地与留痕"），并通过 `/mcp` 把业务能力以 Skills/MCP 形式暴露给 AI 平台调用。

## 仓库结构

```text
apps/web/            # React 19 + Vite 8 + Tailwind 4 前端
apps/server/         # FastAPI + FastMCP 后端（REST :8200/api/v1，MCP :8200/mcp）
packages/contracts/  # orval 从 OpenAPI 生成的 API 类型与 client
docs/                # 技术栈定版、开发流程、各模块开发文档
infra/docker/        # PostgreSQL 等本地基础设施
```

## 快速启动（脚手架落地后生效）

```bash
# 1. 基础设施
cd infra/docker && docker compose up -d

# 2. 后端（REST + MCP 同进程）
npm run dev:server

# 3. 前端
npm install
npm run dev:web
```

## 工程规范

所有开发（人类与 AI 代理）必须先阅读并遵守 [AGENTS.md](AGENTS.md)（`CLAUDE.md` 为其同步镜像）。要点：

- 模块文档先行：开发任何模块前先建 `docs/modules/<module>.md`，每个 PR 同步更新。
- 后端模块化单体：`modules/<module>/{models,schemas,service,router,mcp,tests}`，service 是唯一写库入口。
- MCP 多服务组合：每模块一个 FastMCP 子服务器，`mount(namespace=...)` 统一暴露。
- 前端 feature 切片 + 语义 token 主题 + 类型化 i18n，禁止硬编码文案与裸色值。
- AI 写动作一律走 AgentAction 确认流并全量审计。
