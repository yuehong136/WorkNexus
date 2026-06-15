# WorkNexus 工程规范（CLAUDE.md）

> 本文件是 `AGENTS.md` 的同步镜像，供 Claude Code 读取。**任何规范修改必须在同一提交中同步 `AGENTS.md` 与本文件。**

---

## 1. 项目定位与边界

WorkNexus（智协中枢）是一个 **AI-native 团队协作与工单 WorkOS**：以项目、工作对象（WorkItem）、流程、Intake、AI WorkChat、Skills/MCP 和审计为核心，把人的协作、AI 的建议、系统的执行统一到同一套工作数据底座中。

与已有 AI 平台（multirag，`http://localhost:8123`）的边界划分**不可违反**：

| 系统 | 职责 |
| --- | --- |
| 已有 AI 平台（multirag） | 模型管理、知识库/RAG、智能体编排、工作流编排、MCP Client、Prompt 管理——负责"想和调度" |
| WorkNexus（本项目） | 项目、工单、流程、Intake、仪表盘、权限、审计、业务数据落库，并通过 Skills/MCP 把业务能力暴露给 AI 平台——负责"数据、权限、确认、执行、审计" |

核心安全原则：**AI 平台可以提出动作（AgentAction），WorkNexus 必须校验权限、由人确认、记录审计后才落库。** 本项目内部不做 AI 编排，只做一个薄 AI Adapter 调用已有平台。

---

## 2. 仓库结构

monorepo，前端用 npm workspaces 管理，后端用 uv 独立管理：

```text
WorkNexus/
├── apps/
│   ├── web/          # React 19 前端（npm workspace 成员）
│   └── server/       # FastAPI + FastMCP 后端（uv 管理，不叫 api——它同时提供 REST 与 MCP）
├── packages/
│   └── contracts/    # orval 从后端 OpenAPI 生成的 API 类型 + client（npm workspace 成员）
├── docs/
│   ├── tech-stack.md             # 技术栈定版与升级策略
│   ├── development-workflow.md   # 开发流程
│   └── modules/                  # 每个模块一份开发文档（见第 10 节）
├── infra/docker/     # PostgreSQL 等 docker compose
├── AGENTS.md / CLAUDE.md / README.md
└── package.json      # npm workspaces 根
```

拆包时机约定：`packages/ui`（组件库）与 `packages/skills`（Skill manifest）在出现**第二个消费方**之前不拆，组件留在 `apps/web`，Skill 定义留在 `apps/server`。禁止过早抽象。

---

## 3. 技术栈与版本（定版，禁止私自更换）

版本定版依据与升级策略见 `docs/tech-stack.md`。新增依赖必须用包管理器装最新版（`npm install <pkg>` / `uv add <pkg>`），禁止手写编造版本号。

### 3.1 前端（apps/web）

| 类别 | 选型 | 版本基线 |
| --- | --- | --- |
| 框架 | React | 19.2.x |
| 语言 | TypeScript（strict） | 6.0.x（生态不兼容时允许回退 5.9.x，须记录到 docs/tech-stack.md） |
| 构建 | Vite | 8.0.x |
| 样式 | Tailwind CSS（CSS-first，`@theme`） | 4.3.x |
| 组件 | shadcn/ui（Radix 底座，CLI 生成进仓库） | latest |
| 图标 | lucide-react（唯一图标库） | latest |
| 路由 | react-router（library 模式） | 7.17.x |
| 服务器状态 | @tanstack/react-query | 5.x |
| 客户端状态 | zustand | 5.x |
| 表单 | react-hook-form + zod | 7.x / 4.x |
| 国际化 | i18next + react-i18next（类型化资源） | 26.x / 17.x |
| 测试 | vitest + Testing Library + @playwright/test | 4.x / latest / 1.60.x |
| 质量 | ESLint 10（flat）+ Prettier + husky + lint-staged + commitlint | latest |
| API 类型 | orval（OpenAPI → packages/contracts） | 8.x |

### 3.2 后端（apps/server）

| 类别 | 选型 | 版本基线 |
| --- | --- | --- |
| 语言 | Python | 3.13.x |
| 框架 | FastAPI + Uvicorn | 0.136.x / 0.49.x |
| 数据校验 | Pydantic v2 + pydantic-settings | 2.x |
| ORM | SQLAlchemy 2.0 全异步（asyncpg） | 2.0.x |
| 迁移 | Alembic | 1.18.x |
| 数据库 | PostgreSQL（主系统库，唯一持久化存储） | 17 |
| MCP | fastmcp（多服务组合架构） | 3.4.x |
| 依赖管理 | uv（pyproject.toml + uv.lock，唯一入口，禁止 requirements.txt） | latest |
| 质量 | ruff（line-length 120，check + format）+ mypy + pre-commit | latest |
| 测试 | pytest + pytest-asyncio + httpx AsyncClient | 9.x |

### 3.3 弃用 / 推荐对照表

| 禁止（弃用） | 必须使用 |
| --- | --- |
| Next.js、CRA | Vite + react-router |
| axios | 原生 fetch 封装（`lib/api-client.ts`，统一 `APIError`） |
| antd 及其他重型组件库 | shadcn/ui + Tailwind 4 |
| CSS-in-JS（styled-components 等）、tailwind.config.js 生成 token | Tailwind 4 `@theme` CSS 变量 |
| `dark:` 前缀、`bg-white` / `text-gray-*` 等裸色值 | 语义 token 类（见 5.2） |
| 手写 API 类型文件 | orval 从 OpenAPI 生成 |
| Jest | vitest（唯一前端测试运行器，禁止 `tsx --test` 双轨） |
| redux / mobx | zustand（客户端）+ TanStack Query（服务器） |
| Flask、Django | FastAPI |
| Pydantic v1 风格（`class Config`、`.dict()`） | Pydantic v2（`model_config`、`.model_dump()`） |
| SQLAlchemy 1.x Query API、同步 Session | SQLAlchemy 2.0 `Mapped` + `select()` + AsyncSession |
| YAML + 模块级全局变量配置 | pydantic-settings `BaseSettings`（`WORKNEXUS_` 前缀环境变量） |
| `FastMCP.from_fastapi` 自动转换 | 手写原子化 MCP tools 复用 service 层 |
| poetry / pip + requirements.txt | uv |

---

## 4. 后端架构规范（apps/server）

### 4.1 目录结构：模块化单体（package by domain）

```text
apps/server/
├── pyproject.toml            # uv 管理；ruff / mypy / pytest 配置同文件
├── alembic/                  # 迁移（env.py 从 settings 读 DATABASE_URL）
├── src/worknexus/
│   ├── main.py               # 组装 FastAPI：挂载 /api/v1 与 /mcp，combine_lifespans
│   ├── config.py             # pydantic-settings BaseSettings（.env 驱动）
│   ├── db.py                 # async engine / session factory / Base
│   ├── core/                 # 横切关注点：auth 依赖、Envelope、异常体系、审计中间件、分页
│   ├── api.py                # REST 组合层：聚合各模块 router → /api/v1
│   ├── mcp.py                # MCP 组合层：聚合各模块 FastMCP 子服务器 → mount(namespace=...)
│   └── modules/              # 领域模块，目录即模块边界
│       └── <module>/
│           ├── models.py     # SQLAlchemy 2.0 Mapped 模型
│           ├── schemas.py    # Pydantic v2 schema（独立文件，禁止内联在路由中）
│           ├── service.py    # 业务逻辑（唯一写库入口，REST 与 MCP 共用）
│           ├── router.py     # REST 薄路由
│           ├── mcp.py        # FastMCP 子服务器：原子化 tools/resources，带风险 tag
│           └── tests/        # 模块内单测
└── tests/                    # 跨模块集成测试（httpx AsyncClient + fastmcp Client）
```

v0.1 领域模块：`identity`（身份与权限）、`projects`、`work_items`、`intake`、`workchat`（含 AgentAction）、`skills`（Skill 注册与调用日志）、`dashboards`、`audit`。

分层铁律：

- **service 是唯一写库入口。** `router.py` 与 `mcp.py` 都是薄暴露层，只做参数校验、鉴权依赖、调 service、组装响应，禁止直接操作 session 写库。
- 模块间调用走对方 service 公开函数，禁止跨模块直接 import models 写库。
- 新增领域能力的标准动作：在 `modules/` 下建模块目录，在 `api.py` 与 `mcp.py` 组合层各注册一行。

### 4.2 MCP 多服务架构（FastMCP 3.x）

每个模块在自己的 `mcp.py` 中定义 FastMCP 子服务器，由 `worknexus/mcp.py` 统一组合：

```python
# modules/work_items/mcp.py
from fastmcp import FastMCP

work_items_mcp = FastMCP("WorkItems")

@work_items_mcp.tool(tags={"low_write"})
async def create_work_item(project_id: str, title: str, type: str = "task") -> dict:
    """创建工作项（经 AgentAction 确认流落库）。"""
    ...  # 调 service 层

# worknexus/mcp.py —— 组合层
from fastmcp import FastMCP

mcp = FastMCP("WorkNexus")
mcp.mount(work_items_mcp, namespace="workitem")   # 工具名 → workitem_create_work_item
mcp.mount(projects_mcp, namespace="project")
...

# worknexus/main.py —— 与 FastAPI 同进程共存
from fastmcp.utilities.lifespan import combine_lifespans

mcp_app = mcp.http_app(path="/")
app = FastAPI(lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan))
app.mount("/mcp", mcp_app)
```

MCP 规范铁律：

- **必须**用 `combine_lifespans` 合并 DB lifespan 与 MCP lifespan——漏传 lifespan 会导致 MCP session manager 不初始化。
- **必须**为每个 mount 指定 `namespace`，工具命名自动得到 `<namespace>_<tool>` 前缀。
- tools 必须**原子化、语义化命名**（如 `create_work_item`），禁止"万能工具 + 复杂 DSL 参数"。
- 每个 tool 必须打风险 tag：`read` / `low_write` / `high_write`。`high_write` 工具必须走 AgentAction 确认流（见第 7 节），不允许直接落库。
- 禁止 `FastMCP.from_fastapi` 自动转换 REST 为 MCP。
- MCP 鉴权用 Bearer token（`WORKNEXUS_MCP_AUTH_TOKEN`），调用方身份必须落到 SkillInvocation 与审计日志。

### 4.3 统一响应 Envelope（唯一格式，禁止第二套）

所有 REST 接口统一返回：

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

- `code = 0` 成功；非 0 为业务错误码（`core/errors.py` 集中定义枚举，按模块分段：1xxx 通用、2xxx work_items、3xxx intake……）。
- 列表接口 `data` 内含 `items` + `total` + `page` + `page_size`（统一用 `core/pagination.py` 的 `Page[T]`；经 ApiModel 序列化后 JSON 字段为 camelCase，即 `pageSize`；查询参数保持 `page` / `page_size`）。
- 异常体系：业务异常统一抛 `BizError(code, message)`，由全局 exception handler 转 Envelope；未知异常返回固定文案 `"internal error"` + 日志记录完整堆栈，**禁止把 `str(exc)` 直接返回给客户端**。
- HTTP 状态码：鉴权失败 401、权限不足 403、其余业务错误一律 200 + 非 0 code。
- 统一 `request_id`：中间件为每个请求注入，结构化日志全程携带，错误响应返回该 id 以便追踪。

### 4.4 认证与权限（v0.1 决策，详见 docs/roadmap.md D2/D3）

- 会话：**server-side session + HttpOnly Cookie**（Secure[prod]、SameSite=Lax、DB 只存 token hash）。禁止 localStorage 存会话凭据。MCP 服务间认证用 Bearer token，用户级穿透用 delegation token（见第 7 节）。
- 权限模型：6 个系统角色（`owner/admin/project_admin/member/viewer/ai_agent`）+ 代码常量权限矩阵；只有 `project_members`（项目成员与项目角色）和 `role_bindings`（tenant 级 / AI Agent / 特殊授权）两张表，**同一用户的项目角色禁止双写两表**。
- 校验唯一入口：`core/access.py` 的 `can(subject, action, scope)` 与 `require_permission` 依赖；路由层禁止散落权限 if 判断。
- 前端不自行推导权限，统一消费 `GET /api/v1/me` 的 `CurrentUserContext`；后端永远强制校验。

### 4.5 配置、数据库与迁移

- 配置只用 `config.py` 中的 `Settings(BaseSettings)`，环境变量前缀 `WORKNEXUS_`，通过 `get_settings()`（lru_cache）注入。禁止读 YAML、禁止模块级全局配置变量。
- 全链路 async：路由 `async def` + `AsyncSession`（依赖注入 `Depends(get_db)`）。禁止在 async 路由中调同步阻塞 IO。
- 模型规范：每模块自己的 `models.py`；公共字段 mixin（`id`（uuid7 字符串）、`created_at`、`updated_at`、`tenant_id` 预留）放 `db.py`。禁止把所有模型堆进单文件。
- 任何模型变更必须同 PR 附带 Alembic 迁移：`uv run alembic revision --autogenerate -m "..."`，并人工审查生成的迁移。

---

## 5. 前端架构规范（apps/web）

### 5.1 目录结构：feature-based 切片

```text
apps/web/src/
├── app/                  # 应用骨架：入口、providers（Query/i18n/Theme）、router、AppShell 布局
├── components/
│   ├── ui/               # shadcn/ui 原子组件（CLI 生成；禁止业务逻辑、禁止 API/store）
│   └── patterns/         # PageHeader、DataTable、EmptyState 等复合展示组件（同样禁止 API/store）
├── features/             # 领域切片：home、projects、work-items、board、intake、
│   │                     #   workchat、skills、dashboard、audit、settings
│   └── <feature>/
│       ├── api/          # 调 contracts client + Query Key Factory + use-*-query hooks
│       ├── components/   # 该 feature 专属组件
│       ├── routes/       # 该 feature 页面（路由懒加载入口）
│       └── stores/       # 该 feature 的 zustand store（如需要）
├── lib/                  # api-client（APIError）、query-client、sse 流式、utils
├── stores/               # 全局 store：ui（语言/主题的唯一持久化入口）；auth 不设 store——会话在 HttpOnly Cookie，/me 归 TanStack Query（lib/auth）
├── locales/              # locale-registry.ts + zh-CN/ en-US/（按 feature namespace 分文件）
├── styles/               # globals.css：@theme 语义 token + [data-theme] 变量
└── types/                # 少量全局类型（API 类型一律来自 packages/contracts）
```

分层铁律：

- feature 之间**禁止互相 import**；需要共享时下沉到 `lib/` 或 `components/`。
- `components/ui` 与 `components/patterns` 是纯展示层，禁止调用 API、禁止访问 store。
- 页面/组件层**禁止裸 `fetch`**；所有请求经 `packages/contracts` 生成的 client + TanStack Query hooks。唯一例外：SSE 流式在 `lib/sse.ts` 中封装。
- 单文件理想 <300 行，>400 行必须拆分。
- 命名：文件 `kebab-case.tsx`，导出 `PascalCase` 组件；hooks `use-*.ts`；默认命名导出。

### 5.2 主题规范（强约束）

Tailwind 4 CSS-first，单一真相源在 `styles/globals.css`：

```css
@import "tailwindcss";

@theme {
  --color-surface-primary: var(--surface-primary);
  --color-text-primary: var(--text-primary);
  --color-status-error: var(--status-error);
  /* ... 全部语义 token 经 @theme 映射，业务只见语义名 ... */
}

:root, [data-theme="light"] { --surface-primary: #ffffff; /* ... */ }
[data-theme="dark"] { --surface-primary: #0a0a0b; /* ... */ }
```

铁律：

- 主题切换只改 `html` 的 `data-theme` 属性。唯一入口 `applyTheme(theme)`（`stores/ui.ts` 内实现并由 store action 调用），支持 `light` / `dark` / `system`（system 监听 `prefers-color-scheme`）。**禁止出现第二处写 DOM 或第二个持久化 key**——主题偏好只存在 zustand persist 的 `ui` store 里。
- 业务代码**禁止** `dark:` 前缀（主题差异全部由 CSS 变量承担）、**禁止**裸色值类（`bg-white`、`text-gray-500`、`bg-[#fff]` 等），只允许语义 token 类（`bg-surface-primary`、`text-text-secondary`、`text-status-error`）。ESLint 规则级别为 **error**。
- 图表等 JS 取色场景从 CSS 变量读取（`getComputedStyle`），禁止硬编码色值。

### 5.3 国际化规范（强约束）

- 默认语言 `zh-CN`，支持 `en-US`。`locales/locale-registry.ts` 是语言注册唯一真相源。
- **真实 namespace**：每个 feature 一个 namespace（`common`、`workItems`、`intake`……），按 namespace 分文件、按 locale 目录组织；禁止把所有文案 spread 进单个 translation 对象。
- **类型安全**：通过 i18next `CustomTypeOptions` 声明资源类型，`t()` 的 key 编译期校验；`t('workItems:detail.title')` 写错 key 必须报 TS 错误。
- **单一持久化**：语言偏好只存 zustand persist 的 `ui` store；切换语言唯一入口为 `ui` store 的 `setLanguage()`（内部调 `i18n.changeLanguage`）。禁止 i18next-browser-languagedetector 与 store 双轨存储。
- **禁止硬编码文案**：任何用户可见文案（含常量文件、placeholder、aria-label、toast）必须走 `t()`。i18n 扫描脚本覆盖全部 `src/`，进 CI 为硬门禁。
- 语言资源按 locale **动态 import 分包**，切换时按需加载。
- 新增文案必须同 PR 同时提供 `zh-CN` 与 `en-US`，禁止只写一种语言。

### 5.4 API 与状态规范

- API 类型与 client 由 orval 从后端 OpenAPI 生成到 `packages/contracts`，**禁止手写/手改生成产物**；后端接口变更后运行 `npm run contracts:generate` 同步。
- 自定义 fetch mutator 在 `packages/contracts/src/mutator.ts`：所有请求 `credentials: 'include'`（会话在 HttpOnly Cookie，禁止 JS 持有凭据）、解析 Envelope（`code !== 0` 抛 `APIError(code, message)`）；`APIError` 类以 contracts 包为唯一定义，`lib/api-client.ts` 仅 re-export 并提供 `unwrap()`（orval 响应 → envelope payload）。401 统一在 `lib/query-client.ts` 捕获并 reset me query，由路由守卫重定向。
- 每个 feature 的 `api/keys.ts` 必须用 Query Key Factory 模式（`workItemKeys.list(params)` 等），禁止裸数组 key。
- 服务器状态一律 TanStack Query；zustand 只放纯客户端状态（auth 会话、ui 偏好、临时交互态）。SSE 流式 chunk 不进 Query cache。

---

### 5.5 前端统一写法手册（场景 → 唯一写法，防模块割裂）

> 同一场景在整个项目里**只允许一种写法**。开发新场景前先查本手册；手册没有覆盖的场景，必须在同一 PR 中先补充手册条目（及 patterns 组件）再写业务代码——这是防止不同 agent 各写一套的核心机制。

周边库定版（与第 3 节同级约束，禁止引入同类替代品）：

| 场景 | 唯一选型 | 版本基线 |
| --- | --- | --- |
| Toast 通知 | sonner | 2.0.x |
| 日期处理/格式化 | date-fns | 4.4.x |
| 图表 | recharts | 3.8.x |
| 表格 | @tanstack/react-table（经 `patterns/DataTable` 封装） | 8.21.x |
| 类名合并 | clsx + tailwind-merge（统一经 `cn()`） | 2.x / 3.6.x |
| 组件变体 | class-variance-authority（cva） | 0.7.x |
| 命令面板 | cmdk | 1.1.x |
| Markdown 渲染 | react-markdown + dompurify | 10.x / 3.x |
| 看板拖拽 | @dnd-kit/core | 6.3.x |
| 测试 API mock | msw | 2.14.x |

场景唯一写法：

| 场景 | 唯一写法 |
| --- | --- |
| 数据查询 | `features/<f>/api/` 内 `use<Entity>Query` / `use<Entity>ListQuery`，key 来自该 feature 的 Key Factory；组件内禁止内联 `useQuery` 配置对象超过 queryKey/queryFn/enabled 三项，复杂配置下沉 hook |
| 数据变更 | `use<Action><Entity>Mutation`；成功后用 Key Factory invalidate（禁止手写字符串 key）；错误提示由 `lib/query-client.ts` 全局 `onError` 统一 toast；需要表单内联展示错误的 mutation 声明 `meta: { suppressToast: true }` 并在组件内按错误码映射 i18n 文案 |
| 加载/空/错误三态 | 一律用 `components/patterns/` 的 `PageSkeleton` / `EmptyState` / `ErrorState`；禁止各页面手写 spinner、空白 div 或自定义错误文案布局 |
| 表单 | react-hook-form + `zodResolver` + shadcn `Form/FormField/FormItem/FormMessage` 全链；zod schema 放 `features/<f>/api/schemas.ts`；提交按钮 disabled/loading 绑 `mutation.isPending`；校验文案走 i18n |
| 确认操作 | 统一 `patterns/ConfirmDialog`（封装 shadcn AlertDialog）；禁止 `window.confirm` |
| 弹窗 vs 抽屉 | 短交互（确认、单字段、小表单）用 Dialog；详情查看、长表单、多 Tab 用 Sheet（右侧抽屉）；均为受控 `open` + `onOpenChange` |
| 表格 | 列定义独立 `columns.tsx`（返回 `ColumnDef[]` 的函数，接收 `t` 以支持 i18n），页面只组装 `DataTable` + 数据 hooks |
| 日期显示 | 统一走 `lib/datetime.ts` 的格式化函数（内部用 date-fns + 当前 locale）；禁止组件内散落 `format(date, 'yyyy-MM-dd')` 字符串 |
| 类名 | 动态/合并类名一律 `cn()`；组件多状态样式用 `cva` 定义变体；禁止字符串拼接类名 |
| 路由跳转 | 路径常量集中 `lib/paths.ts`（函数式：`paths.workItem(projectId, id)`）；禁止硬编码路径字符串 |
| zustand 取值 | 一律 selector：`useUIStore(s => s.theme)`；禁止解构整个 store 导致全量重渲染；store 定义含 `persist` + `partialize`（只持久化必要字段） |
| 图表颜色 | 从 CSS 变量读语义 token（`getComputedStyle`），禁止硬编码十六进制色值 |
| 图表（柱/环/折线）封装 | recharts 一律经 `components/patterns/charts/` 的 `BarChart`/`DonutChart`/`LineChart` 薄封装（纯展示层，禁访问 store/API）；系列色由 feature 层经 `lib/chart-colors.ts` 的 `useChartColors()` 从语义 token（`--chart-1..8` 分类色板 / `--status-*` / `--brand-primary`）`getComputedStyle` 解析后**作为 props 传入**封装；axis/grid/tooltip 用 `var(--…)` CSS 变量引用；禁组件内硬编码十六进制、禁在 patterns 图表内读 token/store（取色与主题订阅在 feature/lib 层完成） |
| 全局快捷键/命令 | cmdk 命令面板统一注册，禁止散落 `keydown` 监听 |
| 当前用户上下文/权限控制 | 统一消费 `lib/auth` 的 `useMeQuery`；UI 权限判断只用 `useHasPermission` / `PermissionGate`（`lib/auth`），禁止自行读 cookie、缓存权限或解析角色 |
| 路由守卫 | `features/auth` 的 `RequireAuth`（受保护区）与 `GuestOnly`（login/setup）布局路由；禁止在页面组件内写跳转守卫逻辑 |
| 契约响应解包 | orval 生成的 client 函数返回 `{ data: Envelope, status }`，一律经 `lib/api-client.ts` 的 `unwrap()` 取 payload；禁止手写 `.data.data` 链 |
| AI / Markdown 内容渲染 | 一律经 `lib/markdown.tsx` 的 `Markdown` 组件（react-markdown 渲染 + DOMPurify 先 sanitize 源串、不启用 rehype-raw）；**禁止 `dangerouslySetInnerHTML` 直插**（§7.7 模型输出按不可信输入处理） |
| 看板拖拽 | @dnd-kit（`DndContext` + `useDraggable`/`useDroppable`）；放置到新状态列即调 transition mutation 落库，非法流转由后端 2002 拒绝并 toast；禁止手写 HTML5 `draggable` 事件 |
| AI / 流式 SSE | 唯一封装 `lib/sse.ts` 的 `streamSSE(path, body, { signal, onEvent })`（fetch + ReadableStream + `credentials:'include'`，按 `data:` 分帧 `JSON.parse`，畸形帧跳过不抛）；feature 侧用 `use<Feature>Run` hook 包装（累积流式增量、终态按 Key Factory invalidate）；事件为后端定义的干净 schema（如 `message_delta` / `agent_action` / `done`）；**禁止 `EventSource`**（需 POST + cookie）、禁止页面内裸 fetch 流 |
| AI 动作确认卡片 | 统一 `AgentActionCard`（动作类型 i18n + 参数/diff + 状态 Badge）；卡片本身即确认面：pending 显示 批准/拒绝 直接调 mutation，**不再套 `ConfirmDialog`**；approve/reject 成功按 Key Factory invalidate agentActions；失败（权限/过期等）由 `lib/query-client.ts` 全局 onError toast |
| AI 建议（advisory）卡片 | 统一 `TriageSuggestionCard` 形态：呈现**只读**的 AI 建议（摘要/分类/类型·优先级 + provenance `provider/version`），明确标注"仅供参考、不自动应用"；"采纳建议"按钮只把 suggested_* **预填**进对应的创建/转换表单（如 `ConvertToWorkItemDialog`），落库仍由用户在表单内提交确认。**区别于"确认即执行"的 `AgentActionCard`**——advisory 卡片自身不触发任何写动作 |

### 5.6 后端统一写法手册

| 场景 | 唯一写法 |
| --- | --- |
| 路由签名 | `async def`，依赖注入用 `Annotated` 风格：`db: Annotated[AsyncSession, Depends(get_db)]`、`actor: Annotated[Actor, Depends(get_current_actor)]`；路由函数体 ≤15 行，超出说明逻辑该下沉 service |
| service 函数 | 纯函数式模块（非类）：`async def create_work_item(db, actor, data: WorkItemCreate) -> WorkItem`；第一个参数 db，第二个 actor，第三个起业务参数 |
| 审计写入 | service 内调 `audit.record(db, actor, action, resource, before, after)`，与业务写库同事务 |
| 分页 | 统一 `core/pagination.py` 的 `Page[T]` 泛型 + `page`/`page_size` 查询参数；禁止各模块自定义分页结构 |
| 枚举 | Python `StrEnum` 定义于 `schemas.py`，DB 存字符串；禁止裸字符串字面量散落 |
| MCP tool 返回 | 返回 dict（由 schema `.model_dump()` 产生），错误抛 `fastmcp` 标准异常；禁止返回自由格式文本拼接 |
| MCP tool 鉴权与留痕 | `/mcp` 所有 tool 调用统一经 `modules/skills` 的 `SkillInvocationMiddleware`（双 token：`Authorization: Bearer` server token + `X-WorkNexus-Delegation` delegation；风险门禁：read 执行 / low_write 阻断待 M5 / high_write 拒；每次调用写一行 `skill_invocations`）；tool 内只经 `require_mcp_context()` 取 `(db, actor, delegation)`，禁止 per-tool 自读 header / 自校验 token / 用 tool 参数作身份依据 |
| REST 响应 schema | 一律继承 `core/schemas.py` 的 `ApiModel`（camelCase 别名 + `from_attributes`），路由返回 `Envelope[Schema]` 类型注解使 OpenAPI/orval 拿到完整类型；禁止手写 alias、禁止业务接口返回裸 dict |
| 时间 | 一律 UTC aware datetime（`datetime.now(UTC)`），序列化 ISO 8601；前端负责本地化显示 |

## 6. 数据模型基线（v0.1 核心对象）

核心模型（v0.1 全量表清单见 `docs/reference/v0.1-feature-spec.md` 第 10 节，细节见各模块 `docs/modules/<module>.md`）：`Tenant`、`User`、`Session`、`InviteToken`、`ProjectMember`、`RoleBinding`、`AIAgent`、`McpDelegationToken`、`Project`、`WorkItem`、`WorkItemComment`、`WorkItemActivity`、`WorkItemRelation`、`IntakeRequest`、`Conversation`、`Message`、`AgentAction`、`SkillInvocation`、`AuditLog`。

关键枚举（前后端共享语义，由 contracts 生成保证一致；**枚举常量先于业务代码定死**）：

- `WorkItem.type`: `task | requirement | bug | risk | decision | approval | incident | feedback`
- `WorkItem.status`: `backlog | todo | in_progress | review | done | cancelled`
- `WorkItem.priority`: `low | medium | high | urgent`
- `WorkItem.source`: `manual | ai_chat | intake | api | mcp`
- `WorkItemRelation.type`: `parent_child | blocks | blocked_by | duplicates | relates_to | created_from_message | created_from_intake`
- `IntakeRequest.status`: `new | triaging | accepted | rejected | duplicate | snoozed | converted`
- `AgentAction.status`: `pending | approved | rejected | executed | failed | expired`
- 风险等级（AgentAction / SkillInvocation / MCP tool tag / AuditLog 共用）: `read | low_write | high_write`
- `actor_type` / 评论来源: `user | ai_agent | system`

通用字段约定：所有核心业务表必有 `id / tenant_id / created_at / updated_at`（EntityMixin）；**重要业务表另加 `created_by / updated_by`**，软删除 `deleted_at` 按需。v0.1 不做多租户 UI，tenant_id 仅预留。

---

## 7. AI / Skill 安全规范（不可妥协）

> 身份、权限、AI 对接的完整决策见 `docs/roadmap.md` 第 4 节（D2–D7），此处为执行铁律。

1. **AgentAction 确认流**：AI 产生的写动作一律先创建 `AgentAction(status=pending)`，用户确认后由 service 执行并标记 `executed`；拒绝则 `rejected`。风险等级固定 3 级（`read / low_write / high_write`，禁止新增等级）：`read` 直接执行；`low_write`（创建工作项/Intake、评论、改负责人、状态流转、补字段）默认需确认，可由项目管理员配置部分自动执行；`high_write`（删除、权限变更、审批通过、导出敏感数据、改 Skill 凭证、改流程关键配置）v0.1 禁止 AI 执行。
2. **双重校验公式（写死）**：AI 动作执行前必须满足 用户权限 ∧ AI Agent 权限 ∧ 资源权限 ∧ 风险等级 ∧ 确认状态。WorkNexus 不信任 AI 平台返回的任何权限判断，落库前必须自行校验。
3. **AI 身份穿透**：AI 代表用户调用 `/mcp` 时，身份只认 `X-WorkNexus-Delegation` 短期 delegation token（不透明随机串、DB 存 hash、TTL 5–10 分钟、绑定 tenant/user/agent/project/conversation/run、日志脱敏）。**tool 参数不得作为认证依据**；custom_header 中禁止直传 user_id / email / session token。
4. **AI 上下文权限过滤（底层原则）**：用户看不到的数据，AI 也不能作为上下文读取。任何 AI 上下文构建必须先做权限过滤。
5. **审计必记**：工作项创建/修改/状态流转、AI 建议生成、AgentAction 确认与执行、Skill 调用、权限变化、Skill 配置变化、数据导出。审计写入在 service 层与业务同事务，记录 `actor_type`（user/ai/system）、`actor_id`、资源类型/ID、前后变化；AI 动作另记 `requested_by`、`agent_id`、`approved_by`、`skill_invocation_id`。
6. **SkillInvocation 全量留痕**：每次 MCP tool 调用记录调用方、tool 名、输入/输出摘要、状态、风险等级、是否经确认、关联 audit_log_id。
7. 模型输出按**不可信输入**处理：前端渲染 AI 内容必须经 sanitize（DOMPurify），禁止 `dangerouslySetInnerHTML` 直插。

---

## 8. 测试规范

### 8.1 前端

- 运行器只用 **vitest**（禁止第二运行器双轨）。测试文件与源码同目录：`foo.ts` → `foo.test.ts`。
- 单测优先覆盖：`lib/`、stores、Query hooks（msw mock）、复杂组件交互（Testing Library）。
- E2E 用 Playwright（`apps/web/e2e/`），必须覆盖：核心闭环（创建项目 → 创建工作项 → 看板流转 → 仪表盘变化）、**语言切换**、**主题切换**、登录主路径。
- 禁止快照测试作为主要断言手段。

### 8.2 后端

- pytest markers 分级：`p0`（冒烟，每次 CI 必跑）、`p1`、`p2`、`integration`；`--strict-markers`。
- service 层单测用真实 PostgreSQL（docker compose）+ 事务回滚 fixture，不 mock ORM。
- REST 接口测试用 `httpx.AsyncClient(transport=ASGITransport(app=app))`。
- **MCP tools 测试用 fastmcp in-memory transport**（`async with Client(mcp) as client`），不起 HTTP。
- 覆盖率门槛进 CI：后端语句覆盖率 ≥ 70%（service 层 ≥ 85%），前端 `lib/` + stores ≥ 80%。

---

## 9. 代码风格与注释规范

- **注释最小化**（vibe coding 项目）：默认不写叙述性注释；只在非显而易见的意图、约束、权衡处写。模块的背景与设计沉淀到 `docs/modules/<module>.md`，不写进代码注释。
- 前端：Prettier（`semi: false`、`singleQuote: true`、tailwind 插件排序类名）；ESLint flat config，`react-hooks/exhaustive-deps` 为 error。
- 后端：`ruff check` + `ruff format`（line-length 120）+ mypy（strict 基线），pre-commit 钩子强制。
- 禁止 `any` 滥用（TS）与 `# type: ignore` 滥用（Python），必要时注明原因。

---

## 10. 开发流程规范（文档驱动，强制）

0. **会话必读链**：每个开发会话开始时，按顺序读 `AGENTS.md` → `docs/roadmap.md`（全局蓝图、进度、已敲定决策 D1–D8）→ 对应 `docs/modules/<module>.md`。**对范围、设计、细节有疑问的，必须先与用户讨论敲定，禁止靠假设开发**；大纲（roadmap）的范围与决策变更必须经用户确认。
1. **模块文档先行**：开发任何模块前，先从 `docs/modules/_template.md` 复制创建 `docs/modules/<module>.md`，写清目标、数据模型、API、MCP tools、UI、测试点。
2. **PR 必须同步文档**：每完成一个 PR，必须在同 PR 内更新对应模块文档的"变更记录"小节，并同步 `docs/roadmap.md` 的模块进度。文档未更新的 PR 视为未完成。
3. 提交信息遵循 **Conventional Commits** 且**一律使用英文**（`feat(work-items): ...`、`fix(intake): ...`），commitlint 强制；scope 用模块/feature 名。
4. 分支模型：`main` 保护分支，功能分支 `feat/<module>-<desc>`，修复分支 `fix/<module>-<desc>`。
5. AGENTS.md 与 CLAUDE.md 必须同提交同步；技术栈版本变更必须同步 `docs/tech-stack.md`。
6. CI 硬门禁（建立后逐项启用）：lint、typecheck、i18n 扫描、单测、覆盖率、build、E2E（主链路）。

### 10.1 PR 规范

- **一 PR 一意图**：一个 PR 只做一个模块的一件事（功能、修复或重构，不混合）；纯重构与功能变更必须拆开。业务 diff 理想 ≤400 行（不含生成产物与 locale 文件），超出需在描述中说明原因。
- **PR 标题** = Conventional Commits 格式且使用英文（squash 合并后即提交信息）：`feat(intake): support marking duplicates and linking work items`。
- **PR 描述**使用 `.github/PULL_REQUEST_TEMPLATE.md` 模板，必填：变更摘要（为什么 + 做了什么）、影响面（REST / MCP tools / 数据迁移 / contracts 是否变更）、测试说明、自查清单。
- **自查清单**（模板内置，提交前逐项确认）：
  - [ ] `docs/modules/<module>.md` 变更记录已追加
  - [ ] 新文案 zh-CN 与 en-US 双语齐备，无硬编码
  - [ ] 模型变更附 Alembic 迁移；接口变更已跑 `contracts:generate`
  - [ ] 新场景写法已对齐 5.5/5.6 手册（手册未覆盖的，已在本 PR 补充手册条目）
  - [ ] lint / typecheck / 测试全绿
- **生成产物单独 commit**：`packages/contracts` 生成物、locale 批量变更、shadcn CLI 生成组件各自独立 commit，便于 review 聚焦业务 diff。
- 合并方式：squash merge，保持 main 线性历史。

---

## 11. 常用命令

```bash
# 前端
npm run dev:web              # 启动前端开发服务器
npm run lint:web && npm run test:web

# 后端
cd infra/docker && docker compose up -d        # 启动 PostgreSQL
npm run dev:server           # uvicorn worknexus.main:app --reload --port 8200
npm run test:server          # uv run pytest

# 契约同步（后端 OpenAPI 变更后）
npm run contracts:generate
```

服务端口约定：前端 5173（Vite 默认）、后端 REST `:8200/api/v1`、MCP `:8200/mcp`、PostgreSQL 5432、已有 AI 平台 8123。
