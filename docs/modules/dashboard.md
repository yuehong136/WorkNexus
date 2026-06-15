# 模块：dashboard（项目仪表盘 / 规则版 AI 洞察）

> 状态：设计中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/dashboard`
> 关联 module（后端）：`apps/server/src/worknexus/modules/dashboards`

## 1. 目标与范围

M7 在既有真实业务数据（work_items / intake_requests / work_item_activities）之上，提供**项目级固定仪表盘 + 规则版 AI 洞察卡片**。建立在 M2（projects）、M3（work_items service + 看板 + 活动时间线）、M6（intake）之上，依赖 M1 的权限矩阵（`Permission.DASHBOARD_READ` 已就绪，viewer+ 与 ai_agent 均具备）。

这是一个**几乎纯读、纯聚合**的模块：

```text
GET /projects/{id}/dashboard/summary       → KPI + 状态/类型/优先级/来源分布 + intake 计数 + 近 7 天创建/完成趋势
GET /projects/{id}/dashboard/workload      → 按负责人聚合（含未分配桶）
GET /projects/{id}/dashboard/overdue       → 分页逾期工作项清单（drill-down）
GET /projects/{id}/dashboard/ai-insights   → 规则版洞察数组（风险/逾期/高优先级/负载）+ provenance
```

边界（AGENTS §1）：WorkNexus 负责"数据 / 权限 / 确认 / 执行 / 审计"；本模块只读、不写库、不建表、不产生 AgentAction。AI 洞察 v0.1 **由确定性规则生成**（roadmap D7 明确允许"先规则后 multirag"），为 advisory，**自身不触发任何写动作**。

### 本期与用户敲定的关键设计抉择（A–H）

| 点 | 决策 |
| --- | --- |
| **A AI 洞察** | **规则版 `InsightsEngine`（可替换 Provider，复刻 M6 `TriageEngine`）**。`RuleBasedInsightsEngine`（v0.1，`provider="rules"/version="1"`）+ 未来 `MultiragInsightsEngine`，由 config `dashboard_insights_provider` 选择。**按需算、不缓存、不落库**；time-free（service 盖 `generatedAt`）；每条带 provenance `{provider, version, generatedAt}`。输入为已按项目 scope 的聚合指标——**D6 天然满足**（只含本项目聚合计数，无个体内容跨权限泄漏）。 |
| **B 聚合归属** | **领域 metrics read-model 归各自模块；`dashboards.service` 只编排，不 import 他模块 models**。`work_items.service` / `intake.service` 各暴露**粗粒度**只读 metrics 公开函数（非碎函数）；`dashboards.service` 调它们 + 组装 DTO + 跑洞察引擎。**M3 `get_project_summary` 重构为复用同一 helper**（overdue/high-priority/ai-created 口径单一真相源），不另写一套同口径 SQL。 |
| **口径** | `aiCreatedCount = source IN (ai_chat, mcp)`（**沿用 M3 既有语义，不含 intake**）；新增 `sourceCounts` 全来源分布（manual/ai_chat/intake/mcp/api）；intake 单列 `intakeRequestCount` / `intakeStatusCounts` / `intakeConvertedCount` / `intakeConversionRate`。近 7 天**完成**趋势取自 `work_item_activities`（`action=status_changed` 且 `after.status=done`）的时间，**不用** `updated_at`。 |
| **C 字段** | summary 放 KPI + 四类分布 + intake 计数 + 7 天趋势；overdue 为独立**分页**端点（summary 只放 `overdueCount`）；workload 按负责人聚合（成员数有界，不分页）；ai-insights 返回洞察数组 + provenance。 |
| **D 作用域** | **仅项目级**，全部端点在 `/projects/{id}/dashboard`；不做跨项目 / 租户汇总（Dashboard Builder 是 v0.6）。 |
| **E MCP** | 出 `dashboard_get_project_dashboard` **read** 工具（让 AI 在 WorkChat 读指标），**作为独立 PR ③**（REST 稳定后）；调 `service.get_project_dashboard_snapshot`（**不写 SQL**），返回 summary + workload + overduePreview + aiInsights。read tag 经 `SkillInvocationMiddleware` 直接执行 + 写 `skill_invocations` 留痕。 |
| **F 前端** | `/projects/{id}/dashboard`：KPI 卡（`DashboardCards`）+ 分布图（recharts 环形/柱）+ 7 天创建·完成双折线 + workload `DataTable` + overdue 分页 `DataTable` + AI 洞察卡列（仿 `TriageSuggestionCard` advisory）。**新场景图表封装先补 §5.5 手册再写业务**，图表色从 CSS 变量读语义 token。项目详情页保留精简 `ProjectSummaryCards` + 加「查看仪表盘」入口按钮（gated `dashboard.read`）。 |
| **G 错误码/审计/权限** | **无新错误码**（未知项目复用 `PROJECT_NOT_FOUND=5002`；8xxx 段预留不用）；**读端点不审计**（spec §8 仅要求写动作审计）；MCP 读工具由中间件写 `skill_invocations` 留痕。复用 `dashboard.read` 权限（不改 access.py → 不触发 contracts 连锁）。 |
| **H 表/迁移** | **无新表、无洞察落库 → 无 Alembic 迁移**；仅 `config.py` 加一个 env flag `dashboard_insights_provider`。`alembic check` 应无漂移。 |

### 明确不做 / 推迟

- **multirag 实时洞察** → 后续 provider（M5 端点 live-verify 后）；v0.1 仅规则版。
- **`dashboard_widgets` 可配置仪表盘 / Dashboard Builder** → v0.6（spec §10 明确 v0.1 不建该表）。
- **跨项目 / 租户级汇总、自定义图表、洞察缓存落库** → 推迟。
- **Home「待处理 intake / 我的待办」工作台** → 归 M8（本模块只出项目仪表盘页）。

## 2. 数据模型

**本模块不新建任何表、无模型变更、无 Alembic 迁移。** 只读既有表：

| 既有表 | 读取用途 |
| --- | --- |
| `work_items` | 状态/类型/优先级/来源分布、高优先级数、逾期数、AI 创建数、近 7 天创建趋势、按负责人负载、逾期清单 |
| `work_item_activities` | 近 7 天**完成**趋势（`action=status_changed` 且 `after->>'status'='done'`，按 `date(created_at)` 分组） |
| `intake_requests` | intake 请求数 / 按状态计数 / 转化数 / 转化率（遵循 intake 读时语义，如过期 snooze 惰性回 new） |
| `users` | 负载与逾期清单的 `assignee` 富化（`UserBriefOut`） |

逾期定义（与 M3 `get_project_summary` 一致）：`due_at IS NOT NULL ∧ due_at < now() ∧ status NOT IN (done, cancelled) ∧ deleted_at IS NULL`，按 `tenant_id + project_id` scope。
高优先级定义：`priority IN (high, urgent)`。
AI 创建定义：`source IN (ai_chat, mcp)`。

唯一**非数据库**变更：`config.py` 新增 `dashboard_insights_provider: str = "rules"`（镜像 `intake_triage_provider`，`.env.example` 同步）。

## 3. REST API

统一 `Envelope[...]`，schema 继承 `ApiModel`（camelCase + from_attributes），逾期列表用 `Page[T]`，查询参数保持 `page` / `page_size`。全部 `GET`、只读、项目级。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/dashboard/summary` | KPI + 状态/类型/优先级/来源分布 + intake 计数 + 近 7 天创建/完成趋势 | `dashboard.read`（项目级） |
| GET | `/api/v1/projects/{project_id}/dashboard/workload` | 按负责人聚合（含未分配桶），按 `totalCount` desc | `dashboard.read`（项目级） |
| GET | `/api/v1/projects/{project_id}/dashboard/overdue?page=&page_size=` | 分页逾期工作项清单（drill-down） | `dashboard.read`（项目级） |
| GET | `/api/v1/projects/{project_id}/dashboard/ai-insights` | 规则版洞察数组 + provenance | `dashboard.read`（项目级） |

router 薄路由（≤15 行/个，`Annotated` 依赖，`require_permission(Permission.DASHBOARD_READ, project_param="project_id")`，返回 `Envelope[...]`）；在 `api.py` 注册一行 `api_router.include_router(dashboard_router)`。未知/跨 tenant 项目由 `projects.service.get_project` 抛 `PROJECT_NOT_FOUND=5002`。

### 响应 schema（`modules/dashboards/schemas.py`，全部继承 `ApiModel`）

```text
TrendPoint            { date: str(ISO date), count: int }

DashboardSummaryOut   { totalCount, statusCounts: dict[str,int], typeCounts, priorityCounts,
                        sourceCounts, highPriorityCount, overdueCount, aiCreatedCount,
                        intakeRequestCount, intakeStatusCounts: dict[str,int],
                        intakeConvertedCount, intakeConversionRate: float,
                        createdTrend: list[TrendPoint], completedTrend: list[TrendPoint] }

WorkloadItemOut       { assigneeId: str|None, assignee: UserBriefOut|None, totalCount,
                        statusCounts: dict[str,int], overdueCount, highPriorityCount }
DashboardWorkloadOut  { items: list[WorkloadItemOut] }   # 未分配 = assigneeId None 桶

DashboardOverdueItemOut { id, key, title, status, type, priority, assigneeId,
                          assignee: UserBriefOut|None, dueAt, daysOverdue: int,
                          source, createdAt }
# overdue 端点返回 Page[DashboardOverdueItemOut]
# 排序：due_at asc → priority(urgent>high>medium>low) → created_at desc
# daysOverdue 后端按 UTC aware now 算，前端只展示不自行推导

InsightOut            { kind: InsightKind, severity: InsightSeverity, title: str,
                        detail: str, metrics: dict }
InsightProvenance     { provider: str, version: str, generatedAt: datetime }
DashboardInsightsOut  { insights: list[InsightOut], provenance: InsightProvenance }
```

枚举（`schemas.py`，StrEnum）：
- `InsightKind`: `risk | overdue | high_priority | workload`
- `InsightSeverity`: `info | warning | critical`

### 领域 metrics read-model（B：归各自模块的粗粒度只读公开函数）

`work_items.service`（复用现有 `func.count()/group_by` 风格，参考 `get_project_summary`）：
- `get_project_work_item_metrics(db, actor, project_id)` → 总数 + status/type/priority/source 分布 + highPriorityCount + overdueCount + aiCreatedCount + createdTrend + completedTrend。
- `list_project_overdue_work_items(db, actor, project_id, params: PageParams)` → `(rows, total)`，按上述排序 join assignee。
- `get_project_workload_metrics(db, actor, project_id)` → 按 assignee 分组（含 None 桶）的负载行。
- **重构** `get_project_summary` 复用 `get_project_work_item_metrics` 口径（overdue/high-priority/ai-created 同源），保留 `recent_activities`，**不破坏既有 `ProjectSummaryOut` 契约与现有测试**。

`intake.service`：
- `get_project_intake_metrics(db, actor, project_id)` → requestCount + statusCounts（遵循 intake 读时惰性 snooze 语义）+ convertedCount + conversionRate。

`dashboards.service`（纯函数，`async def fn(db, actor, project_id, ...)`，**无 commit / 无 audit / 无 AgentAction / 不 import 他模块 models**）：
- `get_dashboard_summary` → 调 work_items + intake 领域 metrics，组装 `DashboardSummaryOut`。
- `get_dashboard_workload` → `DashboardWorkloadOut`。
- `get_dashboard_overdue(..., params)` → `Page[DashboardOverdueItemOut]`。
- `get_dashboard_insights` → 取聚合指标 → `get_insights_engine(settings).generate(...)` → 盖 `generatedAt` → `DashboardInsightsOut`。
- （PR③）`get_project_dashboard_snapshot(..., overdue_limit=10)` → 复用上面四者，overdue 只取 preview。

### 规则洞察引擎（`modules/dashboards/insights.py`，复刻 M6 `triage.py`）

```python
class InsightsEngine(Protocol):
    async def generate(self, db, *, project_id, tenant_id, metrics: InsightInput) -> list[Insight]: ...

class RuleBasedInsightsEngine:          # provider = "rules", version = "1"
    async def generate(...) -> list[Insight]: ...   # 忽略 db；按阈值确定性产出

def get_insights_engine(settings: Settings) -> InsightsEngine:
    return RuleBasedInsightsEngine()    # MultiragInsightsEngine 后续按 flag 接入
```

规则（确定性、time-free，输入为已聚合指标）：`overdue`（overdueCount>0，severity 按占比/绝对值阈值升级）、`high_priority`（highPriorityCount 超阈值）、`risk`（type=risk 项 + 逾期 urgent 组合）、`workload`（最高负载远超均值 → 负载失衡）。无触发条件时返回空数组；每条 `metrics` 携带支撑数字。

## 4. MCP Tools

`modules/dashboards/mcp.py` 定义 FastMCP 子服务器，`worknexus/mcp.py` `mcp.mount(dashboard_mcp, namespace="dashboard")`。tool 内只经 `require_mcp_context()` 取 `(db, actor, delegation)`，统一过 `SkillInvocationMiddleware`（双 token + 风险门禁 + 留痕）。**作为独立 PR ③，REST 稳定后再加。**

| Tool（namespace 前缀） | 风险 tag | 是否需确认 | 说明 |
| --- | --- | --- | --- |
| `dashboard_get_project_dashboard` | `read` + `perm:dashboard.read` | 否（直接执行） | 返回项目仪表盘快照：summary + workload + overduePreview（默认 10 条）+ aiInsights，供 AI 在 WorkChat 读项目状态 |

- 入参：`project_id`、`overdue_limit: int = 10`（MCP 只返回 overduePreview + overdueCount，避免大 payload；REST 端点才是分页全量）。
- tool body **不写 SQL**，只调 `dashboards.service.get_project_dashboard_snapshot(...)`，返回 `.model_dump()` dict。
- read tag → 中间件直接执行 + 写一行 `skill_invocations`（留痕）；权限快照基于 delegation 的 `dashboard.read`。

## 5. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/projects/{id}/dashboard` | 项目仪表盘 | `PageHeader` + KPI 卡 `DashboardCards`（总数/高优先级/逾期/AI 创建/intake 请求/转化）+ 分布图（status 环形、type/priority/source 柱）+ 近 7 天创建·完成双折线 `LineChart` + workload `DataTable` + overdue 分页 `DataTable`（columns.tsx）+ AI 洞察卡列（`InsightCard` 仿 `TriageSuggestionCard`，advisory「仅供参考」+ provenance，detail 经 `lib/markdown.tsx`）；三态统一 `PageSkeleton/EmptyState/ErrorState`；入口 `PermissionGate permission="dashboard.read"`（项目详情页按钮 + 路由懒加载于 AppShell/RequireAuth 下） |

- `features/dashboard/api/`：`dashboardKeys` Key Factory；`useDashboardSummaryQuery` / `useDashboardWorkloadQuery` / `useDashboardOverdueQuery`（分页）/ `useDashboardInsightsQuery`（经 contracts client + `unwrap()`）。
- 组件：`DashboardCards`（仿 `project-summary-cards.tsx`）、`StatusDistributionChart` / `TypeDistributionChart` / `PriorityDistributionChart` / `SourceDistributionChart`、`TrendChart`（created vs completed 双折线）、`WorkloadTable`、`OverdueTable`、`InsightCard`（只读 advisory + provenance + 「仅供参考」标注，detail 经 `lib/markdown.tsx`）。
- **图表封装（新场景，§5.5 先补手册再写业务，同步 AGENTS↔CLAUDE）**：`components/patterns/charts/`（`BarChart` / `DonutChart` / `LineChart` 薄封装），颜色经 `lib/chart-colors.ts` 用 `getComputedStyle(document.documentElement).getPropertyValue('--...')` 读语义 token；`styles/globals.css` `@theme` 加分类色板 `--chart-1..--chart-8`（light/dark 各一套，单一真相源）。禁硬编码 hex。
- `lib/paths.ts` 加 `paths.dashboard(projectId)`；`app/router.tsx` 懒加载路由；项目详情页保留精简 `ProjectSummaryCards` + 加「查看仪表盘」入口按钮（gated `dashboard.read`，仿 M6 intake 入口按钮）。

i18n namespace：`dashboard`（zh-CN / en-US 同步提供，四步注册：`locales/i18n.ts` `ns`+`AppTFunction` + `i18next.d.ts` + `zh-CN/dashboard.ts` + `en-US/dashboard.ts`）

- **§5.5 手册补条**（新场景先补手册再写业务，同步 AGENTS↔CLAUDE）：**图表封装 + CSS 变量取色**——分布/趋势图统一经 `components/patterns/charts/` 封装（recharts），系列色一律经 `lib/chart-colors.ts` 从 `globals.css` 语义 token（`--status-*` / `--brand-primary` / `--chart-1..n`）`getComputedStyle` 读，禁组件内硬编码十六进制；切主题/语言图表色随 token 变。

## 6. 审计与权限点

### 审计事件

- **读端点不审计**（spec §8 仅要求工作项写动作 / AI 建议生成 / AgentAction / Skill 调用 / 权限·配置变化 / 数据导出留痕；仪表盘为纯读聚合，不产生这些事件）。
- **MCP 读工具留痕**：`dashboard_get_project_dashboard` 由 `SkillInvocationMiddleware` 写一行 `skill_invocations`（调用方 / tool 名 / 输入输出摘要 / 状态 / 风险等级 read / 关联 audit），无单独 AuditLog。

### 权限点（沿用 M1 矩阵，禁改 access.py）

- `dashboard.read`：查看四个端点 + MCP 快照（viewer+，project_admin/admin/owner 与 ai_agent 均具备；已存在于 `_VIEWER_PERMISSIONS`）。
- 校验唯一入口：REST 走 `require_permission(Permission.DASHBOARD_READ, project_param="project_id")`（项目级 scope）；MCP 走中间件基于 delegation `permissions_snapshot` 的 `dashboard.read`。
- 不新增任何权限点 → 不改 access.py → 不触发 contracts 连锁。

## 7. 测试点

- **领域 metrics 单测**（真实 PG + 回滚 fixture，`work_items/tests` + `intake/tests`）：状态/类型/优先级/来源分布；逾期排序 + `daysOverdue`；按负责人负载（含未分配桶）；近 7 天 created（按 created_at）+ completed（按 status_changed→done 活动）趋势；aiCreatedCount（ai_chat+mcp）与 sourceCounts；intake statusCounts（含过期 snooze 惰性回 new）/ converted / conversionRate。
- **`get_project_summary` 重构回归**：既有 `ProjectSummaryOut` 契约与现有测试不破坏，overdue/high-priority/ai-created 与新 helper 同口径。
- **`insights.py` 规则引擎单测**：各阈值场景确定性输出（overdue/high_priority/risk/workload 的触发与 severity 升级、无触发返回空）；provenance（provider/version）齐备、time-free。
- **dashboards.service 组装单测**：四个 DTO 字段正确；snapshot（PR③）overdue 截断为 preview。
- **REST**（`httpx.ASGITransport`）：四端点返回 Envelope；viewer 可读；未登录 401；未知项目 `PROJECT_NOT_FOUND=5002`；overdue 分页 `page/page_size` 生效。
- **MCP in-memory `Client(mcp)`（PR③）**：`dashboard_get_project_dashboard` read 直接执行 + 写一行 `skill_invocations`；delegation `dashboard.read` 校验。
- **前端（vitest + msw）**：4 个 query hook；`lib/chart-colors` 取色 util。
- **E2E（Playwright，主链路，`WORKNEXUS_AI_CLIENT=fake`）**：创建工作项 → 看板流转到 done → 接受 intake → `/projects/{id}/dashboard` 数字随之更新（§12 step 16）；+ 语言/主题切换图表色随 token 变。
- 覆盖率门槛：后端 service ≥85% / 整体 ≥70%；前端 `lib/` + stores ≥80%。

## 8. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-15 | PR1（设计） | 初版设计：与用户敲定 A–H（A 规则版可替换 `InsightsEngine` 复刻 M6 TriageEngine·按需算不缓存·time-free·带 provenance·D6 天然满足；B 领域 metrics read-model 归各自模块、dashboards 只编排不 import 他模块 models、M3 get_project_summary 重构复用同口径、aiCreatedCount 沿用 ai_chat+mcp 另加 sourceCounts、完成趋势取自 status_changed→done 活动；C summary/workload/overdue 分页/ai-insights 字段契约；D 仅项目级；E read MCP 工具作独立 PR③；F 前端图表封装先补 §5.5 手册、CSS 变量取色、入口按钮；G 无新错误码·读不审计·复用 dashboard.read；H 无新表/无迁移仅加 config flag）；四端点 schema 定型；5 个 PR 拆分（① 设计 ② 后端 ④ contracts ⑤ 前端，③ MCP 独立）；同步 roadmap M7 进度 |
