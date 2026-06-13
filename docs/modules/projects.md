# 模块：projects（项目空间）

> 状态：已上线
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/projects`
> 关联 module（后端）：`apps/server/src/worknexus/modules/projects`（成员写入复用 `modules/identity`）

## 1. 目标与范围

M2 在 M1 身份/权限底座上实现**项目空间**：项目 CRUD 与归档、项目成员管理、项目概览页。项目列表只返回当前用户有 `project.read` 的项目（owner/admin 见全部 active 项目，与 `/me` 的 `projects[]` 同一规则）。

承接 M1：`projects` 表与 `Project` 模型在 M1 已建好（全字段齐备），`ProjectMember` 在 `modules/identity`（D3 划为身份域）。**M2 不新增数据库迁移**——复用既有表，角色变更靠审计 before/after 记录，不加列。

明确不做（v0.1）：
- 工作项相关统计（工作项数/高优先级/逾期数/AI 创建数/最近活动）——依赖 M3 work_items，推迟到 M3，本期概览不含这些字段（不放假 0）。
- 恢复归档（archive 单向，无 unarchive）。
- 项目级 `settings` 编辑（字段保留，UI/接口暂不暴露）。
- 项目级 MCP tools（project-skill 归 M4，见规格书 §4）。
- member 自建项目（`project.create` v0.1 仅 owner/admin）。

## 2. 数据模型

复用 M1 既有表，无新增/变更：

| 模型 | 关键字段 | 说明 |
| --- | --- | --- |
| Project（`modules/projects/models.py`） | `name String(200)`、`key String(20)`（**UNIQUE(tenant_id, key)**）、`description Text?`、`status = active\|archived`、`owner_id FK users?`、`settings JSONB {}`、`created_by?`、`updated_by?` | M1 已建；M2 直接 CRUD |
| ProjectMember（`modules/identity/models.py`，D3 身份域） | `project_id FK projects CASCADE`、`user_id FK users CASCADE`、`role = project_admin\|member\|viewer`、`created_by`、**UNIQUE(project_id, user_id)** | 用户项目角色唯一存放处；写入唯一入口在 `identity.service`，禁止与 role_bindings 双写 |

约束与规则：
- 创建者（owner/admin）**不**写入 ProjectMember——tenant 角色全局生效，无成员行（与 `load_subject` / `/me` 一致）。
- `key` 规范化为大写，正则 `^[A-Z0-9]{2,10}$`；创建时按 `(tenant_id, key)` 预检冲突。
- 成员管理禁止操作 tenant owner（`CANNOT_MANAGE_OWNER_MEMBERSHIP`，对齐 4011 语义）。
- 列表可见性规则（与 `identity.service.build_current_user_context` 一致）：有 tenant 角色 → 全部项目（按 status 过滤）；否则 → `ProjectMember` 命中的项目。默认 `status=active`。

## 3. REST API

错误码占 **5xxx** 段（`core/errors.py`）：

| 码 | 名 | 触发 |
| --- | --- | --- |
| 5001 | PROJECT_KEY_EXISTS | 创建时 `(tenant_id, key)` 冲突 |
| 5002 | PROJECT_NOT_FOUND | 项目不存在或不属于当前 tenant |
| 5003 | MEMBER_ALREADY_EXISTS | 添加已是成员的用户 |
| 5004 | MEMBER_NOT_FOUND | 改/删非成员 |
| 5005 | CANNOT_MANAGE_OWNER_MEMBERSHIP | 通过成员端点管理 tenant owner |

响应统一 `Envelope[...]`，schema 继承 `ApiModel`（camelCase）；列表用 `Page[ProjectOut]`。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/projects?status=&page=&page_size=` | 当前用户可见项目分页（默认 `status=active`） | 仅认证，结果按可见性过滤 |
| POST | `/api/v1/projects` | 创建项目（key 唯一），创建者为 owner | `project.create` |
| GET | `/api/v1/projects/{project_id}` | 项目详情（含 owner brief + memberCount） | `project.read`（项目域） |
| PATCH | `/api/v1/projects/{project_id}` | 改 name/description（key 不可改） | `project.update`（项目域） |
| POST | `/api/v1/projects/{project_id}/archive` | 归档（单向，幂等） | `project.archive`（项目域） |
| GET | `/api/v1/projects/{project_id}/members` | 成员列表（含用户信息，不分页） | `project.read`（项目域） |
| POST | `/api/v1/projects/{project_id}/members` | 添加已有用户为成员 | `project.member.manage`（项目域） |
| PATCH | `/api/v1/projects/{project_id}/members/{user_id}` | 改成员角色 | `project.member.manage`（项目域） |
| DELETE | `/api/v1/projects/{project_id}/members/{user_id}` | 移除成员 | `project.member.manage`（项目域） |

> 列表端点**不挂** `require_permission`（项目级成员无 tenant 角色，tenant-scope 校验会误拒），改为仅认证 + 结果过滤；其余项目内端点用 `require_permission(action, project_param="project_id")`。

**ProjectOut**：`id/name/key/description/status/ownerId/owner{id,displayName,email,avatarUrl}/memberCount/createdAt/updatedAt`（成员数仅统计 `project_members`，不含 owner 本身）。
**ProjectMemberOut**：`userId/displayName/email/avatarUrl/role/createdAt`。

分层：`projects.router` 暴露端点；项目 CRUD → `projects.service`（`create_project`/`get_project_detail`/`list_projects`/`update_project`/`archive_project`，唯一写库入口 + 审计 + commit；`insert_project` 为无审计无 commit 的建块，供 setup 复用）；成员写入 → `identity.service`（`list/add/update_project_member_role/remove_project_member`，因 identity 拥有 project_members，D3）。

## 4. MCP Tools

**无（M2）。** project-skill 的 MCP tools（`get_project_context`/`list_user_projects`/`get_project_summary`）归 M4（规格书 §4）。

## 5. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/projects` | 项目列表 | DataTable（名称/key/状态 Badge/成员数），创建按钮（`PermissionGate project.create`），分页；三态 PageSkeleton/EmptyState/ErrorState |
| `/projects/{id}` | 项目概览 | 名称/描述/负责人/状态/成员数/创建时间；编辑、归档（ConfirmDialog，`project.update`/`project.archive`）；成员管理 section（`PermissionGate project.member.manage`）：成员表 + 添加成员 Dialog + 行内角色 Select + 移除 ConfirmDialog |

i18n namespace：`projects`（zh-CN / en-US 同步提供）。

## 6. 审计与权限点

### 审计事件（action 常量，`audit.service.AuditAction`）

`project.create`、`project.update`、`project.archive`、`project.member.add`（M1 已有）、`project.member.update`、`project.member.remove`。`audit.record()` 与业务写入同事务（service 内 commit）。

### 权限点（沿用 M1 矩阵，禁改）

`project.create`（owner/admin）、`project.read`（全角色 + ai_agent）、`project.update`/`project.archive`/`project.member.manage`（owner/admin/project_admin）。viewer 项目内只读。校验唯一入口 `core/access.py`。

## 7. 测试点

- service / router（`tests/test_projects_api.py`，复用 `conftest.py` db/client/owner_client/initialized/member_user）：
  - p0：未登录列表 401；owner 创建（key 大写归一、唯一）+ 列表见 active；重复 key → 5001。
  - p1 可见性：仅项目成员只见自己项目；列表 id 集合 == `/me` projects ids；archived 默认隐藏、`?status=archived` 可见；未知项目 → 5002。
  - p1 权限：project_admin 可改/归档；项目 member 改项目 → 403；viewer 管成员 → 403。
  - p1 成员：add/update/remove 全链 + 审计断言；重复 add → 5003；改/删非成员 → 5004；管 owner → 5005；项目增改归档写审计。
  - Envelope 形状 + camelCase（`memberCount` 而非 `member_count`）。
- 前端（vitest + msw）：projects 列表查询 hook、创建 mutation、权限 gating、表单 zod 校验（PR2）。
- E2E（Playwright，PR2）：创建项目 → 进概览 → 添加成员 → 改角色 → 移除成员。

## 8. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-13 | PR1（后端） | 项目 CRUD/归档 + 成员管理：5xxx 错误码、`AuditAction.project.*`；`projects.schemas`（ProjectStatus/ProjectMemberRole/ProjectCreate/Update/Out、ProjectMember\* schema）；`projects.service`（`insert_project` 建块 + `create_project`/`get_project_detail`/`list_projects`(可见性复用 build_current_user_context 规则)/`update_project`/`archive_project`，batched owner/memberCount 防 N+1）；`identity.service` 新增成员管理（list/add/update_role/remove，唯一写 project_members + 审计，校验 owner/重复/非成员）；`projects.router` 9 端点（列表仅认证 + 过滤，其余 project_param 权限）+ api.py 注册；`tests/test_projects_api.py` 15 例全绿。**无 Alembic 迁移。** |
| 2026-06-13 | PR2（前端） | `features/projects`：列表页（状态过滤 active/archived + 分页 + 创建）、概览页（基础信息 + 编辑/归档 + 成员管理 section）、成员管理（DataTable + 添加成员 Dialog + 行内角色 Select + 移除 ConfirmDialog）；Key Factory + query/mutation hooks（contracts 解包 `unwrap`，错误内联 5001 映射 i18n，create/update/archive 同时失效 me query 使派生的 `/me.projects` 与权限同步）；`projects` i18n namespace（zh/en）；`lib/paths` + router + AppShell 导航；vitest 5 例（list query + schema 校验）；E2E `projects.spec.ts`（创建项目→添加成员→改角色→移除，workers=1 串行）。复用既有原生 styled select / DataTable / ConfirmDialog / PermissionGate 模式，未新增写法手册条目。 |
