# 模块：work_items（工作对象 + Workflow Lite + 看板）

> 状态：已上线
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/work-items`、`apps/web/src/features/board`
> 关联 module（后端）：`apps/server/src/worknexus/modules/work_items`（概览统计端点同属本模块）

## 1. 目标与范围

M3 在 M1 身份/权限底座与 M2 项目空间之上落地 **工作对象**：8 种类型的 WorkItem、固定状态机
（Workflow Lite）、Markdown 评论、站内活动时间线、7 类关系、List 视图、看板（Board），以及本模块
自己的 MCP 工具。它是 **自 M1 以来第一个要写 Alembic 迁移** 的模块（4 张新表 + projects 加一列）。

验收（规格书 §3）：8 类型可建；List + 看板可用；流转写 **双日志**（活动 + 审计）；详情见评论/活动/
来源/AI 摘要；AI 创建的项有 `source` 标记；权限不足不可见不可改。

本模块严格复用 M1/M2 写法：service 是唯一写库入口并与 `audit.record` 同事务；
`require_permission(project_param=...)`；`Envelope`/`ApiModel`/`Page[T]`；`BizError`/`ErrorCode`；
前端 Key Factory + `unwrap` + `PermissionGate`/`useHasPermission` + DataTable/ConfirmDialog/patterns +
原生 styled `<select>` + i18n 四步注册 + `paths.ts` + 路由懒加载。

明确不做（v0.1）：动态字段配置 / 复杂条件必填 / 关系图可视化 / 工作流可配置（v0.3）/ 批量编辑 / 附件 /
关注订阅 / 保存视图（v0.2）；`created_from_message`、`created_from_intake` 关系仅建表与展示，由 M5/M6
系统写入；`/mcp` 双 token（server token + delegation）中间件与 `skill_invocations` 全量留痕属 M4，本期
MCP 工具仅复用 M1 已有的 `verify_delegation_token`，尚未受 server-token 中间件保护。

## 2. 数据模型

通用：四张表均用 `EntityMixin`（id `String(32)` uuid hex / `tenant_id` / `created_at` / `updated_at`）。
枚举为 `schemas.py` 中 `StrEnum`，DB 存字符串。时间一律 UTC `TIMESTAMP(timezone=True)`。

| 模型 | 关键字段 | 说明 |
| --- | --- | --- |
| WorkItem（`work_items`） | `project_id FK projects CASCADE`（索引）、`seq Integer`（**UNIQUE(project_id, seq)**）、`key String(40)`（**持久化**，创建时 `f"{project.key}-{seq}"`，**UNIQUE(project_id, key)**）、`type`、`title String(300)`、`description Text?`（Markdown）、`status`、`priority`、`assignee_id FK users?`（索引）、`reporter_id FK users?`、`due_at TIMESTAMP?`、`tags JSONB []`、`source`、`source_ref_id String(64)?`、`ai_summary Text?`、`acceptance_criteria Text?`、`custom_fields JSONB {}`、`created_by/updated_by String(32)`、`deleted_at TIMESTAMP?` | `key` 持久化而非读时拼接：`project.key` 不可改，存值永不失效，且便于按 key 直接搜索/展示；`seq` 为排序与唯一性真相源。索引 `(project_id, status)`、`assignee_id`。软删除：list/get 过滤 `deleted_at IS NULL` |
| WorkItemComment（`work_item_comments`） | `work_item_id FK CASCADE`（索引）、`author_type String(20)`（`user\|ai_agent\|system`）、`author_id String(32)?`、`body Text`（Markdown） | 评论作者用 author_type/author_id 表达（需支持 AI/系统评论） |
| WorkItemActivity（`work_item_activities`） | `work_item_id FK CASCADE`（索引）、`actor_type/actor_id`、`action String(50)`、`field String(50)?`、`before JSONB?`、`after JSONB?` | 站内活动时间线，**独立于** `audit_logs`（安全审计）；action 见 ActivityAction 枚举 |
| WorkItemRelation（`work_item_relations`） | `source_work_item_id FK CASCADE`（索引）、`target_work_item_id FK CASCADE`（索引）、`type String(30)`、`created_by`、**UNIQUE(source, target, type)** | 服务层守卫 `source != target`；blocked_by 为 blocks 的反向展示，不独立手动建 |
| Project（`modules/projects/models.py`，alter） | 新增 `work_item_seq Integer NOT NULL server_default '0'` | 项目内序号计数器（key 生成） |

**迁移**：`uv run alembic revision --autogenerate -m "work_items tables and project sequence"` 后人工审查
（FK CASCADE、唯一约束、projects 列回填默认值）。

### 枚举（schemas.py，StrEnum）

- `WorkItemType`: `task | requirement | bug | risk | decision | approval | incident | feedback`
- `WorkItemStatus`: `backlog | todo | in_progress | review | done | cancelled`
- `WorkItemPriority`: `low | medium | high | urgent`
- `WorkItemSource`: `manual | ai_chat | intake | mcp | api`
- `RelationType`: `parent_child | blocks | blocked_by | duplicates | relates_to | created_from_message | created_from_intake`
- `ActivityAction`: `created | title_changed | description_changed | assignee_changed | priority_changed | status_changed | commented | relation_added | relation_removed | deleted`
- `CommentAuthorType` / `ActorType`: `user | ai_agent | system`

## 3. 状态机（Workflow Lite）

`ALLOWED_TRANSITIONS`（schemas.py 常量，严格按规格书 §3）：

```
backlog     → {todo, cancelled}
todo        → {in_progress, cancelled}
in_progress → {review, cancelled}
review      → {done, in_progress, cancelled}   # review→in_progress 为唯一回退边
done        → {}                               # 终态
cancelled   → {}                               # 终态
```

`transition_work_item` 校验目标 ∈ 允许集，否则 `BizError(INVALID_STATUS_TRANSITION)`；同事务写
**活动（`status_changed`）+ 审计（`work_item.transition`）**。

## 4. custom_fields 类型专属字段（后端轻校验）

`schemas.py` 为每个 `WorkItemType` 定义一个 Pydantic 模型（`model_config = ConfigDict(extra="forbid")`，
字段全可选、校验基础类型），由 `CUSTOM_FIELD_SCHEMAS` 字典索引：

- Bug：`severity / steps_to_reproduce / expected_result / actual_result / environment / affected_version`
- Requirement：`business_goal / user_value / boundary_conditions / dependencies`
- Risk：`risk_level / impact / probability / mitigation_plan / trigger_condition`
- Decision：`background / options / decision_result / decision_owner / impact_scope`
- Approval：`approval_type / approvers / approval_status / approval_comment`
- task / incident / feedback：空模型（仅允许 `{}`）

`validate_custom_fields(type, data)` 在 service 层调用，REST **与** MCP 路径共用；未知键 / 基础类型错误
→ `BizError(INVALID_CUSTOM_FIELDS)`。`acceptance_criteria` 为顶层独立列（requirement/approval 共用），
**不** 重复进 Requirement 的 custom 模型。

## 5. 服务层业务规则（service 强制，REST + MCP/AI 共用）

- **来源 server 派生（不信任客户端 provenance）**：`source`/`source_ref_id` 由入口在 service 内设置，
  不从请求体读取。REST 手动 UI → `manual`；`work_items/mcp.py` AI 工具 → `mcp`（delegation 含会话时
  `ai_chat`）；Intake 转化（M6）→ `intake`；外部 API（未来）→ `api`。创建 schema **不暴露**
  `source`/`source_ref_id` 为客户端可设字段——由调用方作为显式 service 参数传入。保证 AI 创建项被诚实
  标记（验收 §3），防伪造 AI 来源。
- **assignee / reporter 校验**：传入 `assignee_id`（或 `reporter_id`）时，校验用户存在、同 tenant、且对该
  项目有访问权（tenant 角色 **或** 该项目 `ProjectMember`），否则 `BizError(INVALID_ASSIGNEE)`；
  `reporter_id` 缺省取创建 actor。创建、更新、改负责人时均适用。
- **归档项目写阻断**：所有写（create / update / transition / comment / relation add/remove）先加载父项目，
  `project.status != active` 则 `BizError(PROJECT_ARCHIVED)`；读（list/get/activities）仍允许。统一
  helper `ensure_project_writable(db, project_id, tenant_id)`。

## 6. REST API

错误码占 **2xxx** 段（`core/errors.py`）：

| 码 | 名 | 触发 |
| --- | --- | --- |
| 2001 | WORK_ITEM_NOT_FOUND | 不存在 / 不属于当前 tenant / 已软删除 |
| 2002 | INVALID_STATUS_TRANSITION | 目标状态不在允许集 |
| 2003 | COMMENT_NOT_FOUND | |
| 2004 | RELATION_NOT_FOUND | |
| 2005 | INVALID_RELATION | 自链 / 不支持手动创建的类型 / 跨项目 |
| 2006 | RELATION_ALREADY_EXISTS | (source, target, type) 重复 |
| 2007 | INVALID_CUSTOM_FIELDS | 未知键 / 基础类型错误 |
| 2008 | INVALID_ASSIGNEE | assignee/reporter 非该项目可用用户 |
| 2009 | PROJECT_ARCHIVED | 归档项目下的写操作被阻断 |

响应统一 `Envelope[...]`，schema 继承 `ApiModel`（camelCase）；列表用 `Page[WorkItemOut]`。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/work-items?status=&type=&priority=&assignee_id=&page=&page_size=&sort=` | 项目下工作项分页 | `work_item.read`（project_param） |
| POST | `/api/v1/projects/{project_id}/work-items` | 创建工作项（key 自增、source=manual） | `work_item.create`（project_param） |
| GET | `/api/v1/work-items/{id}` | 详情 | `work_item.read`（工作项依赖） |
| PATCH | `/api/v1/work-items/{id}` | 改 title/description/priority/assignee/due_at/tags/ai_summary/acceptance_criteria/custom_fields | `work_item.update` |
| DELETE | `/api/v1/work-items/{id}` | 软删除 | `work_item.delete` |
| POST | `/api/v1/work-items/{id}/transition` | 状态流转 | `work_item.transition` |
| GET/POST | `/api/v1/work-items/{id}/comments` | 评论列表/新增 | `work_item.read` / `work_item.comment` |
| GET | `/api/v1/work-items/{id}/activities` | 活动时间线 | `work_item.read` |
| GET | `/api/v1/work-items/{id}/relations` | 关系列表（含 incoming/outgoing 方向 + 对端 brief；规格书 §3 外新增，详情抽屉需要） | `work_item.read` |
| POST | `/api/v1/work-items/{id}/relations` | 新建关系（4 类手动；同项目、非自链、去重） | `work_item.update` |
| DELETE | `/api/v1/work-items/{id}/relations/{relation_id}` | 删关系 | `work_item.update` |
| GET | `/api/v1/projects/{project_id}/summary` | 项目概览统计（M2 推迟字段） | `work_item.read` / `project.read`（project_param） |

**平铺端点权限作用域（已知 403 坑）**：`modules/work_items/deps.py` 的
`require_work_item_permission(action)` 依赖工厂——按 `work_item_id` 路径参数加载工作项（不存在/跨 tenant/
软删除 → 404），取其 `project_id`，做 **项目作用域** `can()` 校验，把加载的工作项缓存到 `request.state`
供处理函数复用，返回 `Subject`。嵌套 `/projects/{project_id}/work-items` 端点用既有
`require_permission(action, project_param="project_id")`。

### 输出 schema（ApiModel，camelCase，批量加载 user 防 N+1）

- `WorkItemOut`：含持久化 `key`、`assignee` brief、全字段
- `CommentOut`：`id/workItemId/authorType/authorId/author?/body/createdAt`
- `ActivityOut`：`id/workItemId/actorType/actorId/actor?/action/field/before/after/createdAt`
- `RelationOut`：`id/type/sourceWorkItemId/targetWorkItemId/target{key,title,status,type}/createdAt`
- `ProjectSummaryOut`：`totalCount`、`statusCounts{}`、`highPriorityCount`（priority∈high/urgent）、
  `overdueCount`（due_at<now ∧ status∉{done,cancelled}）、`aiCreatedCount`（source∈ai_chat/mcp）、
  `recentActivities[]`

## 7. MCP Tools（`modules/work_items/mcp.py`）

`work_items_mcp = FastMCP("WorkItems")`，6 个原子工具薄封装 **同一 service 层**：

| Tool（含 namespace 前缀） | 风险 tag | 是否需确认 | 说明 |
| --- | --- | --- | --- |
| `workitem_create_work_item` | low_write | 是（M5 AgentAction 流） | 创建工作项，source=mcp |
| `workitem_update_work_item` | low_write | 是 | 改字段 |
| `workitem_transition_work_item` | low_write | 是 | 状态流转 |
| `workitem_comment_work_item` | low_write | 是 | 加评论（author=ai_agent） |
| `workitem_search_work_items` | read | 否 | 项目内按条件检索 |
| `workitem_get_work_item` | read | 否 | 取详情 |

context helper 从 `X-WorkNexus-Delegation` header 经 M1 既有 `verify_delegation_token` 还原 actor，并从
session factory 开 db。server-token 中间件 + `skill_invocations` 留痕属 M4。组合层
`worknexus/mcp.py`：`mcp.mount(work_items_mcp, namespace="workitem")`。

## 8. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/projects/{id}/work-items` | List 视图 | DataTable（key/类型/标题/状态/优先级/负责人）+ 筛选（status/type/priority/assignee 原生 select）+ 分页 + 创建 Dialog（`PermissionGate work_item.create`）；三态 PageSkeleton/EmptyState/ErrorState |
| `/projects/{id}/board` | 看板 | 6 状态列 + `@dnd-kit` 拖拽流转；卡片显示负责人/优先级/类型/AI 来源 Badge |
| `/work-items/{id}`（WorkItemDrawer，右侧 Sheet） | 详情抽屉 | 字段 + 内联编辑（rhf+zodResolver+Form）、状态流转、评论（react-markdown + DOMPurify）、活动时间线、关系面板（4 类手动建/删）、来源与 AI 摘要展示 |
| `/projects/{id}`（概览，M2 页扩展） | 概览统计卡 | 消费 `GET /projects/{id}/summary` |

i18n namespace：`workItems`（zh-CN / en-US 同步提供，四步注册）。工作项 mutation **不** 失效 `me`
（权限由已缓存的项目角色派生）。新增 shadcn 组件（单独 commit）：`sheet`、`textarea`。

## 9. 审计与权限点

### 审计事件（`audit.service.AuditAction` 新增）

`work_item.create`、`work_item.update`、`work_item.delete`、`work_item.transition`、`work_item.comment`、
`work_item.relation.add`、`work_item.relation.remove`。与业务写入同事务；**流转/创建等同时写
work_item_activities（站内时间线）形成"双日志"**。

### 权限点（沿用 M1 矩阵，禁改）

`work_item.read`（全角色 + ai_agent）、`work_item.create/update/transition/comment/assign`
（owner/admin/project_admin/member + ai_agent caps）、`work_item.delete`（owner/admin/project_admin）。
viewer 项目内只读。校验唯一入口 `core/access.py`。

## 10. 测试点

- **service 单测**：key 并发自增（并行创建无重复 seq）；状态机真值表（合法/非法流转）；custom_fields
  按类型拒绝未知键/类型错误；source server 派生不可被请求体覆盖；assignee/reporter 非项目用户被拒
  （2008）；归档项目写阻断（2009）；软删除后不可见/不可改；活动 + 审计同事务（回滚则双消失）。
- **router 单测**：平铺 `/work-items/{id}` 对非成员/viewer 的项目作用域 403；Envelope + camelCase；分页与
  筛选；transition 双日志断言。
- **MCP in-memory 测试**：`async with Client(mcp)` 校验 6 工具注册、风险 tag、读/写行为。
- **前端（vitest + msw）**：List 查询 hook、zod schema、看板拖拽交互、summary 卡片。
- **E2E（Playwright）**：创建工作项 → List 可见 → 看板拖拽流转（状态持久化）→ 打开 Drawer → 加评论 →
  流转 → 活动时间线；并保持语言/主题切换绿。

## 11. 参考实现对照（Plane，/Users/dxl/project/ts/plane）

| 维度 | Plane | WorkNexus（本设计） | 理由 |
| --- | --- | --- | --- |
| 序号生成 | `pg_advisory_xact_lock(project)` + `MAX(sequence)+1` + 独立 IssueSequence 表 | projects 加 `work_item_seq` 列 + 原子 `UPDATE … RETURNING` | 单语句行锁，无需 advisory lock 与扫描，按项目天然串行、不阻塞其他项目 |
| 角色/权限 | 数字角色阈值比较 | D3 命名角色 + 权限点矩阵 | AI 参与需细粒度权限点与风险分级 |
| 活动记录 | IssueActivity（业务时间线兼审计） | work_item_activities（站内）+ audit_logs（安全审计）双轨 | 本产品核心诉求是 AI 安全参与，安全审计独立不可省 |
| 富文本 | description_html + 前端富文本 | description/comment 存 Markdown，react-markdown + DOMPurify 渲染 | §7.7 模型输出按不可信输入处理，强制 sanitize |
| 关系 | IssueRelation（blocking/blocked/duplicate/relates）| 7 类 RelationType，M3 手动 4 类，created_from_* 系统预留 | 为 AgentAction/Intake 链路预留来源关系 |

借鉴：sequence 并发用项目级串行；看板/详情 peek 抽屉交互范式；关系类型集合。**不照搬** Django 实现、
数字角色、富文本 HTML 存储。

## 12. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-13 | （设计） | 初版设计：4 张表 + projects.work_item_seq；持久化 key（项目内 seq 原子自增）；8 类型/固定状态机/custom_fields 后端轻校验；服务层三铁律（source server 派生、assignee/reporter 校验、归档写阻断）；2xxx 错误码；REST + 平铺端点工作项权限依赖；6 个 MCP 工具（low_write/read）复用 verify_delegation_token；GET /projects/{id}/summary；前端 List + 看板(@dnd-kit) + WorkItemDrawer(Sheet) + react-markdown/dompurify；6 PR 拆分；对照 Plane Issues |
| 2026-06-13 | PR1（后端核心） | 4 张表模型 + projects.work_item_seq 列 + Alembic 迁移（35d6bb78933b，FK CASCADE / (project_id,seq)·(project_id,key) 唯一 / no_self_relation CHECK / seq 列默认 0）；schemas（5 枚举 + ALLOWED_TRANSITIONS + 8 类型 custom_fields 模型 extra=forbid + In/Out）；service（key 原子自增 `UPDATE…RETURNING`、create/get/list(筛选+排序)/update/delete[软删]/transition，活动+审计双日志，validate_custom_fields/ensure_project_writable/_ensure_assignable 三铁律，批量加载 assignee 防 N+1）；deps.require_work_item_permission（平铺端点项目作用域）；REST 6 端点 + api.py 注册；errors 2001–2009；AuditAction work_item.*；9 个测试（key 自增/状态机/双日志/软删/custom_fields/assignee/归档阻断/viewer 403/非成员 403）全绿，累计 90 passed；ruff/mypy/alembic upgrade head 通过 |
| 2026-06-13 | PR2（评论/活动/关系） | schemas 增 CommentCreateIn/CommentOut、ActivityOut、RelationCreateIn/RelationOut/WorkItemBriefOut/RelationDirection + MANUAL_RELATION_TYPES（parent_child/blocks/relates_to/duplicates）；service 增 list/create_comment（Markdown，author=actor.type，活动+审计）、list_activities（按 actor 批量加载 user）、list/create/delete_relation（同项目+非自链+去重，incoming/outgoing 方向，软删对端跳过）；REST 增 6 端点（comments GET/POST、activities GET、relations GET/POST/DELETE）；无迁移；4 个测试（评论增列、活动时间线、关系全生命周期、关系拒绝自链/非手动类型/跨项目）全绿，累计 94 passed |
| 2026-06-13 | PR3（概览统计 + MCP） | service.get_project_summary（totalCount/statusCounts/highPriorityCount/overdueCount/aiCreatedCount/recentActivities）+ GET /projects/{id}/summary（work_item.read 项目作用域）+ ProjectSummaryOut/ProjectActivityOut；work_items/mcp.py 6 工具（create/update/transition/comment 打 low_write、search/get 打 read），_delegated 经 X-WorkNexus-Delegation + M1 verify_delegation_token 还原 ai_agent actor（server-token 中间件与 AgentAction 确认流属 M4/M5），组合层 mount(namespace="workitem")；3 个测试（summary 统计、MCP 工具注册+风险 tag、缺 delegation 被拒）全绿累计 97 passed；contracts:generate 同步（单独 commit），web typecheck 通过 |
| 2026-06-13 | PR4（前端 List + 概览统计） | `features/work-items`：Key Factory、useWorkItemsQuery/useCreateWorkItemMutation（unwrap，create 失效 list）、zod create schema、2xxx 错误内联映射、workItemColumns（type/status/priority 语义 Badge 变体）、WorkItemFormDialog（type/title/description/priority，原生 styled select）、WorkItemsPage（status/type/priority 筛选 + 分页 + 创建，PermissionGate work_item.create 项目作用域 + 返回项目链接）；`features/projects` 增 useProjectSummaryQuery + ProjectSummaryCards（统计卡 + 最近活动），概览页接入并加「工作项」入口（assignee 选择/筛选随 PR5 抽屉补）；i18n workItems namespace 四步注册（含 i18n.ts ns/AppTFunction）+ projects:summary/detail.workItems 文案（zh/en）；paths.workItems + router 懒加载路由；web typecheck/lint(0 err)/test(18)/build 全绿 |
| 2026-06-13 | PR6（前端看板 + E2E） | 两 commit：① 加 @dnd-kit/core 依赖 + AGENTS/CLAUDE §5.5（周边库 + 看板拖拽写法手册条目）+ tech-stack 同步；② 看板（落在 features/work-items 以遵守 feature 不互 import）：board-card（useDraggable，点击开抽屉/拖拽改状态）、board-column（useDroppable，data-status）、board（DndContext + PointerSensor distance:8 + DragOverlay，放置即调 useBoardTransitionMutation，非法流转 2002 toast，viewer 无 sensors 只读）、board-page（6 状态列 + List/Board 切换 + 抽屉）；ALLOWED_TRANSITIONS 前端镜像；paths.board + router 路由 + 列表页「看板视图」入口；E2E `work-items.spec.ts`（创建项目→工作项→抽屉评论→流转→活动→看板鼠标拖拽 todo→in_progress 持久化）全绿，3 个 e2e 通过；web typecheck/lint(0 err)/test(20)/build 全绿。看板拖拽单测因 dnd 在 jsdom 难以模拟，由 E2E 覆盖 |
| 2026-06-13 | PR5（前端 WorkItemDrawer） | 三 commit：① 加 react-markdown/dompurify 依赖 + AGENTS/CLAUDE §5.5（周边库 + 新写法手册条目 lib/markdown.tsx）+ tech-stack 同步；② 手写 shadcn `sheet`（右侧 Radix Dialog）+ `textarea`（语义 token）；③ 功能：`lib/markdown.tsx`（react-markdown + DOMPurify 先 sanitize 源串，禁 dangerouslySetInnerHTML）+ markdown.test；11 个 query/mutation hooks（detail/update/transition/delete/comments/activities/relations/members）；WorkItemDrawer（右侧 Sheet：头部 key/type/source badge、状态流转 select[ALLOWED_TRANSITIONS]、编辑表单[title/description/priority/assignee/acceptance + per-type custom_fields 镜像决策 B]、删除 ConfirmDialog、字段/Markdown 描述/AI 摘要、评论[Markdown 渲染+发表]、活动时间线、关系[4 类手动建/删 + incoming/outgoing 方向]）；列表行标题打开抽屉 + assignee 筛选补齐；work-item-badges 共享组件；web typecheck/lint(0 err)/test(20)/build 全绿 |
