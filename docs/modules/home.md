# 模块：home（工作台 / 跨项目「我的」聚合）

> 状态：设计中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/home`
> 关联 module（后端）：`apps/server/src/worknexus/modules/home`

## 1. 目标与范围

工作台 Home 是登录后的落地页（`/`），回答「**我现在要看什么**」。M8 把现有占位页（`home.title` + `home.placeholder`）做成跨项目「我的」聚合**快照**：

```text
GET /api/v1/home   → { myTodos, overdue, pendingAgentActions, recentAiCreated, pendingIntake }
                     每组形如 { total: int, items: [top-N] }
```

五张卡：

1. **我的待办**（work_items：assignee=我、非终态、跨项目）
2. **逾期**（work_items：assignee=我、`due_at < now`、非终态）
3. **待确认 AI 动作**（agent_actions：status=pending、我可见项目）——**一等公民**，置顶/高亮
4. **最近 AI 创建**（work_items：`source ∈ {ai_chat, mcp}`、我可见项目、按 created_at desc）
5. **待处理 Intake**（intake_requests：非终态 = `ACTIONABLE_STATUSES`、我可见项目）

边界（AGENTS §1 + M7 decision B）：Home 是**概览**不是第二套跨项目列表中心。**完整分页继续交给已有工作项/Intake/AI 页**；每个卡片项带足够字段供前端 `paths.*` 深链回既有页。Home **纯读、无副作用、不写审计、不建表、不暴露 MCP**。

### 本期与用户敲定的关键设计抉择（A–G）

| 点 | 决策 |
| --- | --- |
| **A 接口形态** | **单快照端点 `GET /api/v1/home`** + 各卡 `{total, items: top-N}` 截断预览（N 固定，如 8）。**不做** `/home/todos` 这类分页端点（避免重造 work-items/intake 的过滤·分页·空态·跳转）。「查看更多」深链到已有页（带可表达的筛选状态）。 |
| **B 编排归属** | **新建 `modules/home`，沿用 M7 decision B**：`home.service.get_home_snapshot(db, actor)` **只编排领域 read service 公开函数，不 import 他模块 models、不直接拼 SQL**。参考 `modules/dashboards/service.py`。 |
| **C 领域 read 函数** | 现有领域函数多为**按项目**；跨项目「我的」需在对应领域模块**补公开 read 函数**（read-model 归各自模块），而非在 home 里 import models。复用：`workchat.service.list_agent_actions`（已支持 `accessible_project_ids` + `status=pending`）；新增：work_items 三个（assigned-open / my-overdue / recent-ai-created）、intake 一个（pending）。 |
| **D 可访问项目集** | 把 `projects.service._accessible_project_ids(subject)` 升级/包公开 `accessible_project_ids(subject) -> set[str] | None`（None=owner/admin 全租户）。各新域函数签名约定接 `project_ids: set[str] | None`（None=全租户），内部按 `project_id IN (...)` + `tenant_id` 一次查询返回 top-N + total。 |
| **E recentAiCreated 语义** | 「我可见项目内最近 AI 创建」**非仅 assignee=我**（区别于 myTodos/overdue 的「我的」）；口径 `source ∈ {ai_chat, mcp}` 沿用 M3/M7 `aiCreatedCount`。 |
| **F 权限** | Home = **登录即可**（`get_current_actor`，无额外权限点）。数据可见性由「可访问项目集 + assignee 过滤」天然满足 D6（看不到的项目不进聚合）。后端永远强制按 `accessible_project_ids` 过滤。 |
| **G 错误码/审计/表/迁移/MCP** | **无新错误码**（8xxx 空闲）；**Home 读不写审计**；**无新表、无迁移**（`alembic check` 无漂移）；**无 MCP 工具**。 |

### 明确不做 / 推迟

- 跨项目「我的工作」全量分页列表页 / 第二套列表中心 → 推迟（v0.2 保存视图/分组/高级筛选）。
- Home 卡片可配置 / 自定义工作台 → 推迟。
- 站内通知 / Inbox → v0.2。

## 2. 数据模型

**本模块不新建任何表、无模型变更、无 Alembic 迁移。** 只读既有表，且**经领域 service 公开函数**（不直接读他模块 models）：

| 既有表（经对方 service） | 读取用途 |
| --- | --- |
| `work_items`（work_items.service） | myTodos（assignee=我·非终态）、overdue（assignee=我·due_at<now·非终态）、recentAiCreated（source∈ai_chat/mcp） |
| `agent_actions`（workchat.service） | pendingAgentActions（status=pending·可见项目） |
| `intake_requests`（intake.service） | pendingIntake（status∈ACTIONABLE_STATUSES·可见项目） |
| `projects`（projects.service） | 可访问项目集 `accessible_project_ids`、卡片项的 project 名 |

非终态定义：work_items `status NOT IN (done, cancelled)`；intake `ACTIONABLE_STATUSES = {new, triaging, snoozed}`（intake 读时惰性 snooze 语义由 intake.service 负责）。

## 3. REST API

统一 `Envelope[...]`，schema 继承 `ApiModel`。单端点、只读、登录即可。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/home` | 工作台快照：五卡各 `{total, items: top-N}` | 登录（`get_current_actor`） |

router 薄路由，`operation_id="get_home"`，返回 `Envelope[HomeSnapshotOut]`；`api.py` 注册一行。

### 响应 schema（`modules/home/schemas.py`，继承 `ApiModel`）

```text
HomeCardOut[ItemT]    { total: int, items: list[ItemT] }   # 泛型；total=全量计数，items=top-N 预览

HomeSnapshotOut       { myTodos:            HomeCardOut[HomeWorkItemOut],
                        overdue:            HomeCardOut[HomeOverdueItemOut],
                        pendingAgentActions: HomeCardOut[AgentActionOut],   # 复用 workchat schema
                        recentAiCreated:    HomeCardOut[HomeWorkItemOut],
                        pendingIntake:      HomeCardOut[HomeIntakeOut] }

# item schema 尽量复用各域已有 Out 的精简投影，带足够字段供 paths.* 深链：
HomeWorkItemOut   { id, key, projectId, title, type, status, priority, assigneeId, source, dueAt, createdAt }
HomeOverdueItemOut{ id, key, projectId, title, status, type, priority, dueAt, daysOverdue, createdAt }
HomeIntakeOut     { id, projectId, title, status, source, createdAt }
# pendingAgentActions 直接用 workchat 的 AgentActionOut（含 projectId/conversationId/actionType/riskLevel/status）
```

> 复用既有 Out 优先；新建精简投影仅为减小 payload。若直接复用 `WorkItemOut` 更省事且 payload 可接受，实现时可二选一（在 PR 中说明）。

### service（`modules/home/service.py`，纯函数、无 commit/audit/AgentAction、不 import 他模块 models）

```python
async def get_home_snapshot(db, actor) -> HomeSnapshotOut:
    subject = ...                      # 由 router 注入（require auth 得 Subject/Actor）
    pids = projects_service.accessible_project_ids(subject)   # set[str] | None
    todos   = await work_items_service.list_assigned_open_work_items(db, actor, project_ids=pids, limit=N)
    overdue = await work_items_service.list_my_overdue_work_items(db, actor, project_ids=pids, limit=N)
    actions = await workchat_service.list_agent_actions(db, actor,
                  accessible_project_ids=pids, params=PageParams(1, N), status=PENDING)
    recent  = await work_items_service.list_recent_ai_created_work_items(db, actor, project_ids=pids, limit=N)
    intake  = await intake_service.list_pending_intake(db, actor, project_ids=pids, limit=N)
    # 组装 HomeSnapshotOut（每组 total + items）
```

### 新增领域 read-model 公开函数（read-model 归各自模块）

`work_items.service`（复用现有 `select/func.count/group_by` 风格）：
- `list_assigned_open_work_items(db, actor, *, project_ids, limit)` → `(items, total)`：`assignee_id=actor.id ∧ status∉{done,cancelled}`，按 `priority desc → due_at asc nulls last → created_at desc`。
- `list_my_overdue_work_items(db, actor, *, project_ids, limit)` → `(items, total)`：`assignee_id=actor.id ∧ due_at<now ∧ status∉{done,cancelled} ∧ deleted_at IS NULL`，含 `days_overdue`（UTC 后端算），排序同 dashboard overdue。
- `list_recent_ai_created_work_items(db, actor, *, project_ids, limit)` → `(items, total)`：`source∈{ai_chat,mcp}`，`created_at desc`（语义为可见项目内最近 AI 创建，非仅 assignee）。

`intake.service`：
- `list_pending_intake(db, actor, *, project_ids, limit)` → `(items, total)`：`status∈ACTIONABLE_STATUSES`（遵循读时惰性 snooze），`created_at desc`。

`workchat.service`：复用既有 `list_agent_actions(db, actor, *, accessible_project_ids, params, status, project_id=None)`，无需新函数。

`projects.service`：公开 `accessible_project_ids(subject) -> set[str] | None`（包/升级现有 `_accessible_project_ids`）。

> 统一约定：`project_ids=None` 表示 owner/admin 全租户（不加 `project_id IN` 约束，仅 `tenant_id` scope）；非 None 时加 `project_id IN project_ids`。所有新函数一次查询返回 `(top-N items, total)`，`total` 为该卡全量计数。

## 4. MCP Tools

**无。** Home 是用户 UI 聚合，不是 AI 能力（AI 读项目状态走 M7 `dashboard_get_project_dashboard`）。

## 5. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/`（替换占位） | 工作台 Home | 五卡网格：**待确认 AI 动作**置顶/高亮（一等公民，仿 `AgentActionCard` 摘要 + count）+ 我的待办 / 逾期 / 最近 AI 创建 / 待处理 Intake。每卡 = 标题 + count `Badge` + top-N 列表（精简行）+ 「查看更多」深链。三态统一 `PageSkeleton/EmptyState/ErrorState`；卡片样式参考 `features/dashboard/components/dashboard-cards.tsx` |

- `features/home/api/`：`homeKeys`（`homeKeys.snapshot()`）+ `useHomeQuery()`（contracts `getHome` + `unwrap()`，`staleTime` 短使确认/创建后刷新）。
- 深链（`lib/paths.ts`，皆已存在）：工作项 → `paths.workItems(projectId)` / `paths.board(projectId)`；agent action → `paths.ai(projectId)`；intake → `paths.intake(projectId)`。
- 组件：`HomeCard`（通用：标题 + count + 列表 + 查看更多）+ 五个 item 行渲染器；待确认动作行可复用 workchat 既有展示元素（不跨 feature import → 必要时下沉到 `components/`）。

i18n namespace：`home`（zh-CN / en-US 同步提供，四步注册）；扩展现占位 `home.title`/`home.placeholder` 为完整卡片文案。

## 6. 审计与权限点

### 审计事件

- **Home 读不写审计**（纯读聚合，不产生 spec §8 要求的写事件）。

### 权限点（沿用 M1，禁改 access.py）

- 无新权限点。Home 端点仅 `get_current_actor`（登录即可）；数据可见性由后端按 `accessible_project_ids` + assignee 强制过滤（D6：看不到的项目/他人的待办不进聚合）。
- 前端无需 `PermissionGate`（登录即见），但各卡片项深链目标页仍各自有权限校验。

## 7. 测试点

- **领域新函数单测**（真实 PG + 回滚 fixture，各归 `work_items/tests` + `intake/tests`）：assigned-open（assignee 过滤 + 非终态 + 排序 + total）；my-overdue（due_at<now + assignee + days_overdue + 排序）；recent-ai-created（source∈ai_chat/mcp + created_at desc）；pending-intake（ACTIONABLE_STATUSES + 惰性 snooze）；`project_ids=None`（全租户）vs 具体集合（仅含集合内项目）。
- **home.service 组装单测**：五卡 total/items 正确；owner/admin 见全租户、member 仅见自己项目（跨项目隔离）；空数据返回空 items + total=0。
- **REST**（`httpx.ASGITransport`）：登录返回 Envelope[HomeSnapshotOut]；未登录 401；member 与 owner 看到不同聚合。
- **前端（vitest + msw）**：`useHomeQuery` hook；`HomeCard` 渲染（count/空态/查看更多链接）。
- **E2E（Playwright 主链路）**：创建工作项（assignee=自己）→ Home「我的待办」出现；AI 动作确认前 Home「待确认 AI 动作」可见该动作（§12 闭环）——并入 home/E2E PR。
- 覆盖率门槛：后端 service ≥85% / 整体 ≥70%；前端 `lib/` + stores ≥80%。

## 8. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-16 | PR2（后端聚合） | 新建 `modules/home`（`schemas.py`：泛型 `HomeCardOut[T]{total, items}` + `HomeSnapshotOut` 复用各域 Out〔WorkItemOut/OverdueWorkItem/AgentActionOut/IntakeOut〕；`service.get_home_snapshot(db, subject)` 沿用 decision B 只编排不 import 他模块 models，HOME_CARD_LIMIT=8；`router.py` `GET /home` 依赖 `get_current_subject`〔登录即可〕→ `Envelope[HomeSnapshotOut]`；`api.py` 注册）；领域补公开 read 函数：`work_items.service` 三个（`list_assigned_open_work_items` / `list_my_overdue_work_items` / `list_recent_ai_created_work_items`，签名 `project_ids: set[str]|None`，None=全租户、空集=无访问）+ 抽 `_build_overdue_outs` 共享 days_overdue；`intake.service.list_pending_intake`（ACTIONABLE_STATUSES，读时不改 snooze）；workchat 复用既有 `list_agent_actions`。`projects.service._accessible_project_ids` → 公开 `accessible_project_ids`（/me·/projects·/home 一致）。测试 +5（service 3：五卡聚合·member 无项目全空〔D6〕·member 仅见本人 assigned；API 2：owner 五卡 envelope·401）；全套 244 passed，ruff/mypy 全绿，alembic check 无漂移。无新表/迁移/MCP。 |
| 2026-06-16 | PR1（设计） | 初版设计：与用户敲定 A–G（A 单快照端点 `GET /home` + 各卡 {total, top-N}、不做分页端点、查看更多深链；B 新建 home 模块沿用 M7 decision B 只编排不 import 他模块 models；C 领域补公开 read 函数、复用 workchat.list_agent_actions；D `projects.accessible_project_ids` 公开化、各域函数接 project_ids=None 全租户；E recentAiCreated 为可见项目内 source∈ai_chat/mcp 非仅 assignee；F 登录即可、按可访问项目集强制过滤满足 D6；G 无新错误码/读不审计/无表无迁移/无 MCP）；`HomeSnapshotOut`/`HomeCardOut` schema 定型；五卡数据来源与排序口径定型；同步 roadmap M8 进度 |
