# 模块：audit（审计查询页 / 读侧收尾）

> 状态：设计中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/audit`
> 关联 module（后端）：`apps/server/src/worknexus/modules/audit`

## 1. 目标与范围

审计**写侧**从 M1 起已横切落地：`audit.service.record(db, actor, *, action, resource_type, ...)` 与各业务写动作**同事务**写一行 `audit_logs`（身份/AI 动作链/Skill 调用/权限·配置变化等）。但 `modules/audit/` 至今**只有 `models.py` + `service.py`，没有任何查询端点**。

M8 给审计补**读侧收尾**：一个 tenant 级审计查询页，从**安全/合规视角**回放系统里发生过的动作，清晰呈现「人 vs AI vs 系统」三类来源与 **AI 确认链**（提案 → 批准 → 执行）。

```text
GET /api/v1/audit-logs   → 分页审计行（按 actor/resource/project/action/时间过滤，created_at desc）
```

边界（AGENTS §1）：本模块**纯读、不写库、无 audit-of-audit、不建表、不暴露 MCP 工具**。审计是 tenant 级安全能力，不是项目活动流。

### 本期与用户敲定的关键设计抉择（A–G）

| 点 | 决策 |
| --- | --- |
| **A 端点形态** | **单个 `GET /api/v1/audit-logs`**（tenant 级），不加 `/projects/{id}/audit-logs`——项目过滤用 `project_id` 查询参数即可覆盖。spec §8 列的两个端点收敛为一个 + 过滤参数。 |
| **B 权限** | 沿用 tenant 级 `Permission.AUDIT_READ`（**仅 owner/admin**，已存在于矩阵），**不改 access.py**、**不下放 project_admin**。审计含登录/邀请/权限绑定/Skill/AgentAction/系统设置等跨项目或无项目事件，天然 tenant 级。项目级审计若要做，应作独立 PR 重新设计可见性屏蔽，不混进 M8。 |
| **C 过滤维度** | `actor_type`、`actor_id`、`resource_type`、`resource_id`、`project_id`、`action`、`created_from`、`created_to`（皆可选）；统一 `Page[T]` 分页；排序固定 `created_at desc`。 |
| **D actor 名解析** | 审计行只存 `actor_type` + `actor_id`；列表按页**批量解析**展示名：`user`→`User.display_name`、`ai_agent`→`AIAgent.name`、`system`→`displayName=None`。沿用既有跨模块只读 precedent（`work_items._users_by_ids` / `skills._load_users` 均直接 `select(User)`）；在 `identity.service` 加公开 `get_users_by_ids` / `get_agents_by_ids` 集中复用（`AIAgent` 在 `identity/models.py`）。 |
| **E AI 确认链呈现** | **不 denormalize**。`requested_by`/`approved_by` 在 `agent_actions` 表（非审计行），`skillInvocationId`/`actionType` 在审计行 `detail` JSONB。按 `resource_type=agent_action` + `resource_id` 过滤即得链路行序列：`ai.proposed_action.create`(actor=agent) → `agent_action.approve`(actor=user) → `agent_action.execute`(actor=agent)。前端用 actor 类型 Badge 区分人/AI/系统；`detail.skillInvocationId` 链到 `/skills`。 |
| **F SkillInvocation** | 调用日志浏览**仍留 `/skills`**（M4 已有 `GET /skills/invocations`），不在审计页重做第二套调用列表；审计页只展示 `skill.invoke` 审计行并交叉链接到 `/skills` invocation 详情。 |
| **G 错误码/审计/表/迁移** | **无新错误码**（8xxx 仍空闲）；**读端点不审计**；**无新表、无迁移**（`alembic check` 应无漂移）；**无 MCP 工具**。 |

### 明确不做 / 推迟

- 项目级 `audit.read` 下放、`/projects/{id}/audit-logs` 路由、`project.audit.read` 新权限点 → 后置独立设计。
- 审计行导出、保留期/归档策略、审计页内嵌 SkillInvocation 全量列表 → 推迟。
- 审计写侧任何改动（写侧 M1 已就绪，M8 不动）。

## 2. 数据模型

**本模块不新建任何表、无模型变更、无 Alembic 迁移。** 只读既有 `audit_logs`（`modules/audit/models.py`，`AuditLog(EntityMixin, Base)`）：

| 列 | 类型 | 读取用途 |
| --- | --- | --- |
| `id` / `created_at` | str / datetime（EntityMixin） | 行标识 + 排序键（`created_at desc`） |
| `tenant_id` | str | **scope**：永远 `== actor.tenant_id` |
| `actor_type` | str(20) | 来源类型 `user / ai_agent / system`（Badge） |
| `actor_id` | str(64)\|None | 解析展示名（user/agent）；system 为空 |
| `action` | str(100) | 动作（`AuditAction` 值，如 `agent_action.execute`），i18n 映射 |
| `resource_type` / `resource_id` | str(50) / str(64)\|None | 资源（AI 链过滤键：`agent_action` + id） |
| `project_id` | str(32)\|None | 项目过滤 + 展示项目名 |
| `before` / `after` / `detail` | JSONB\|None | 前后变化 + 额外上下文（`detail.skillInvocationId` / `detail.actionType`） |
| `request_id` / `ip_address` | str(36) / str(45)\|None | 追踪信息 |

`AuditAction`（`audit/service.py` StrEnum，现 32 个值）覆盖 setup/auth/invite/role_binding/project/work_item/skill/ai.proposed_action/agent_action/intake 全链；**M8 settings 写动作新增 `USER_PROFILE_UPDATE = "user.profile.update"`（见 settings.md，由 settings PR 加，本 PR 不加）**。

## 3. REST API

统一 `Envelope[...]`，schema 继承 `ApiModel`（camelCase + from_attributes），列表用 `Page[T]`（查询参数保持 `page` / `page_size`）。只读、tenant 级。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/audit-logs?page=&page_size=&actor_type=&actor_id=&resource_type=&resource_id=&project_id=&action=&created_from=&created_to=` | 分页审计行，`created_at desc`，多维可选过滤 | `audit.read`（tenant 级，owner/admin） |

router 薄路由（`Annotated` 依赖，`require_permission(Permission.AUDIT_READ)`，**无 `project_param`** → tenant 级校验），`operation_id="list_audit_logs"`，返回 `Envelope[Page[AuditLogOut]]`；`api.py` 注册一行 `api_router.include_router(audit_router)`。

### 响应 schema（`modules/audit/schemas.py`，全部继承 `ApiModel`）

```text
AuditActorType        StrEnum: user | ai_agent | system
AuditActorOut         { type: AuditActorType, id: str | None, displayName: str | None }
                      # system → id=None, displayName=None; user/ai_agent → 解析后展示名

AuditLogOut           { id, createdAt, actor: AuditActorOut, action: str,
                        resourceType: str, resourceId: str | None,
                        projectId: str | None, projectName: str | None,
                        before: dict | None, after: dict | None, detail: dict | None,
                        requestId: str | None, ipAddress: str | None }
# 列表端点返回 Page[AuditLogOut]；action/resourceType 原值，前端按值 i18n 映射可读文案
```

### service（`modules/audit/service.py`，在既有 `record` 旁加只读 list）

```python
async def list_audit_logs(
    db, actor, *, params: PageParams,
    actor_type=None, actor_id=None, resource_type=None, resource_id=None,
    project_id=None, action=None, created_from=None, created_to=None,
) -> tuple[list[AuditLogOut], int]:
    # select(AuditLog).where(tenant_id == actor.tenant_id) + 各可选过滤
    # order_by(created_at desc) + offset/limit；count() 求 total
    # 批量解析本页 actor_id → displayName（user/agent），project_id → projectName
```

- actor 解析复用 `identity.service.get_users_by_ids(db, ids)` / `get_agents_by_ids(db, ids)`（本 PR 在 identity 补这两个公开只读 helper，集中两处既有 `select(User)` 散写）。
- project 名解析复用 `projects.service`（公开只读批量取项目名；若无则按 precedent 直接 `select(Project)` 批量）。
- 纯函数、不 commit、无 audit-of-audit。

## 4. MCP Tools

**无。** 审计不暴露给 AI（敏感、tenant 级安全数据）。

## 5. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/audit` | 审计查询页 | `PageHeader` + 过滤条（`actor_type`/`resource_type`/`action` select、`project` select〔来自 `/me` projects〕、日期范围）+ `DataTable`（columns.tsx）分页；行展开/点击经 `Sheet` 看 `before/after/detail` JSON；actor 列按 `type` 用 `Badge` 区分 人/AI/系统 + 展示名；`detail.skillInvocationId` 链 `/skills`；三态统一 `PageSkeleton/EmptyState/ErrorState`；入口 `PermissionGate permission="audit.read"`（仅 owner/admin 可见），路由懒加载于 AppShell/RequireAuth 下 |

- `features/audit/api/`：`auditKeys` Key Factory（`auditKeys.list(params)`）；`useAuditLogsQuery(params)`（contracts `listAuditLogs` + `unwrap()`）。
- 组件：`audit-columns.tsx`（返回 `ColumnDef[]` 的函数，接 `t`：时间用 `lib/datetime` `formatDateTime`、actor Badge、action/resourceType i18n 映射、project 名、detail 触发 Sheet）、`audit-filter-bar.tsx`、`audit-detail-sheet.tsx`（before/after/detail JSON 只读 + Skill 链接）。
- `lib/paths.ts` 加 `audit: () => '/audit'`；`app/router.tsx` 懒加载；app-shell 加 `<PermissionGate permission="audit.read">` 导航项。

i18n namespace：`audit`（zh-CN / en-US 同步提供，四步注册：`locales/i18n.ts` `ns`+`AppTFunction` + `i18next.d.ts` + `zh-CN/audit.ts` + `en-US/audit.ts`）。`action` / `resourceType` / `actorType` 的人类可读文案全部经 `t()` 映射，禁硬编码。

## 6. 审计与权限点

### 审计事件

- **读端点不审计**（spec §8 仅要求写动作留痕；审计查询为纯读，不产生事件、不写 audit-of-audit）。

### 权限点（沿用 M1 矩阵，禁改 access.py）

- `audit.read`：查看 `/audit` 页与端点。**仅 owner/admin**（tenant 级；矩阵中 admin 起具备，project_admin/member/viewer/ai_agent 均无）。
- 校验唯一入口：`require_permission(Permission.AUDIT_READ)`（无 `project_param` → tenant scope）。前端 `useHasPermission('audit.read')` / `PermissionGate` 控制导航与页面可见，后端永远强制校验。
- 不新增任何权限点 → 不改 access.py → 不触发 contracts 连锁。

## 7. 测试点

- **service 单测**（真实 PG + 回滚 fixture）：各过滤维度（actor_type/actor_id/resource_type/resource_id/project_id/action/created_from/created_to）单独与组合；分页 `page/page_size`；排序 `created_at desc`；actor 名解析（user→display_name、ai_agent→name、system→None）；**tenant 隔离**（不返回他 tenant 行）；AI 链按 `resource_type=agent_action`+`resource_id` 过滤得 propose→approve→execute 序列。
- **REST**（`httpx.ASGITransport`）：owner/admin 可读返回 Envelope[Page]；member/viewer 403；未登录 401；过滤参数生效。
- **前端（vitest + msw）**：`useAuditLogsQuery` hook；actor Badge / action 映射渲染。
- **E2E（Playwright 主链路）**：AI 动作确认后，`/audit` 查到该 `agent_action` 的全链行（propose→approve→execute，人/AI/系统 Badge）——并入 home/E2E PR（§12 step 15）。
- 覆盖率门槛：后端 service ≥85% / 整体 ≥70%；前端 `lib/` + stores ≥80%。

## 8. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-16 | PR2（后端读侧） | `audit/schemas.py`（`AuditActorType` StrEnum + `AuditActorOut` + `AuditLogOut`）；`audit/service.py` 加 `list_audit_logs`（tenant scope + actor_type/actor_id/resource_type/resource_id/project_id/action/created_from/created_to 可选过滤 + `created_at desc` + 分页 + 按页批量解析 actor/project 名）+ 泛型 `_names_by_ids[M: (User, AIAgent, Project)]` + `_to_out`；`audit/router.py` `GET /audit-logs`（`require_permission(AUDIT_READ)` tenant 级，`action: AuditAction \| None` / `actor_type: AuditActorType \| None` 给 contracts 枚举）；`api.py` 注册 audit_router。**实现偏差**：actor/project 名直接 `select(User/AIAgent/Project)` 内联解析（沿用 skills._load_users / work_items._users_by_ids 既有 precedent），**未**在 identity.service 加 get_users_by_ids/get_agents_by_ids——因 audit 被各模块写路径 import，引入 identity.service 会形成循环 import。测试 +11（service 6：actor 名解析 user/agent/system·过滤 actor_type/action/resource·project 名·desc+分页·tenant 隔离·AI 链按 resource=agent_action+id 得 propose→approve→execute；API 5：owner 读+actor 富化·action 过滤·401·member 403·project_admin 仍 403 证明不下放）；全套 239 passed，ruff/mypy 全绿，alembic check 无漂移。无新表/迁移/MCP。 |
| 2026-06-16 | PR1（设计） | 初版设计：与用户敲定 A–G（A 单端点 `GET /audit-logs` tenant 级、项目过滤用查询参数；B 沿用 tenant 级 `audit.read` 仅 owner/admin、不改 access.py、不下放 project_admin；C 过滤维度 actor/resource/project/action/时间 + Page[T] + created_at desc；D actor 名按页批量解析 user/agent/system、identity 补 get_users_by_ids/get_agents_by_ids；E AI 链不 denormalize，按 resource=agent_action+id 过滤得 propose→approve→execute；F SkillInvocation 仍留 /skills 加交叉链接；G 无新错误码/读不审计/无表无迁移/无 MCP）；`AuditLogOut`/`AuditActorOut` schema 定型；同步 roadmap M8 进度 |
