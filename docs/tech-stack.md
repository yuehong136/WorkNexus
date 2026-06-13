# 技术栈定版（2026-06-12 核实）

本文件记录版本定版依据与升级策略。规范层面的约束见 `AGENTS.md` 第 3 节；两边必须同步。

## 版本核实方式

所有版本号于 2026-06-12 通过 `npm view <pkg> version` 与 PyPI API 实时核实。新增依赖一律用包管理器安装最新版（`npm install <pkg>` / `uv add <pkg>`），禁止手写版本号。

## 前端（apps/web）

| 依赖 | 定版 | 说明 |
| --- | --- | --- |
| react / react-dom | 19.2.7 | |
| typescript | 6.0.3 | 若 ESLint/vitest 生态出现不兼容，允许回退 5.9.x 并在本文件记录 |
| vite | 8.0.16 | |
| tailwindcss | 4.3.0 | CSS-first，`@theme` 定义语义 token，无 tailwind.config.js |
| shadcn/ui | CLI latest | 使用 Tailwind 4 模板初始化；组件生成进仓库 |
| react-router | 7.17.0 | library 模式（非 framework 模式） |
| @tanstack/react-query | 5.101.0 | |
| zustand | 5.0.14 | |
| react-hook-form + zod | 7.x / 4.4.3 | |
| i18next / react-i18next | 26.3.1 / 17.0.8 | CustomTypeOptions 类型化资源 |
| vitest | 4.1.8 | 唯一前端测试运行器 |
| @playwright/test | 1.60.0 | E2E |
| eslint / prettier | 10.4.1 / latest | flat config |
| orval | 8.17.0 | OpenAPI → packages/contracts |
| lucide-react | latest | 唯一图标库 |
| sonner | 2.0.7 | 唯一 toast |
| date-fns | 4.4.0 | 唯一日期库（经 lib/datetime.ts 统一封装） |
| recharts | 3.8.1 | 唯一图表库（颜色从 CSS 变量取） |
| @tanstack/react-table | 8.21.3 | 经 patterns/DataTable 封装 |
| clsx + tailwind-merge | 2.1.1 / 3.6.0 | 统一经 cn() |
| class-variance-authority | 0.7.1 | 组件变体 |
| cmdk | 1.1.1 | 命令面板 |
| react-markdown | 10.1.0 | Markdown 渲染（经 lib/markdown.tsx，不启用 rehype-raw） |
| dompurify | 3.4.10 | 不可信内容 sanitize（与 react-markdown 配合，§7.7） |
| @dnd-kit/core | 6.3.1 | 看板拖拽（DndContext + useDraggable/useDroppable） |
| msw | 2.14.6 | 测试 API mock |

## 后端（apps/server）

| 依赖 | 定版 | 说明 |
| --- | --- | --- |
| python | 3.13.x | |
| fastapi | 0.136.3 | |
| uvicorn | 0.49.0 | |
| pydantic / pydantic-settings | 2.x / 2.14.1 | v2 风格（model_config / model_dump） |
| sqlalchemy | 2.0.50 | 全异步 + asyncpg |
| alembic | 1.18.4 | |
| postgresql | 17 | 主系统库，唯一持久化存储 |
| fastmcp | 3.4.2 | 多服务组合（mount + namespace），与 FastAPI 同进程 |
| uv | 0.11.x | 唯一依赖管理入口 |
| ruff | 0.15.x | line-length 120，check + format |
| pytest | 9.0.3 | + pytest-asyncio + httpx |

## 升级策略

- 小版本/补丁：每月集中升级一次，跑全量 CI 后合入。
- 大版本：先在 `docs/modules/` 对应文档登记影响面，单独 PR 升级。
- 任何版本变更必须同步本文件与 `AGENTS.md` 第 3 节。
