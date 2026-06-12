# 模块：identity（身份与权限）

> 状态：开发中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/auth`、`apps/web/src/features/settings`（members 页）、`apps/web/src/lib/auth`
> 关联 module（后端）：`apps/server/src/worknexus/modules/identity`（+ `modules/audit` 起步、`modules/projects` 仅模型）、`core/access.py`

## 1. 目标与范围

M1 是 v0.1 所有模块的前置底座：本地账号认证（邮箱+密码，server-side session + HttpOnly Cookie）、首启 `/setup` 初始化、邀请制用户激活、6 系统角色 + 代码常量权限矩阵（`core/access.py` 唯一校验入口）、AI Agent 身份与 delegation token 签发/校验（供 M4/M5 使用）、审计写入起步。

明确不做（v0.1）：SSO/OIDC 实接（仅 `identity_provider`/`external_user_id` 字段预留）、multirag 账号实际同步、邮件发送（邀请走复制链接）、动态 RBAC 表（v0.9 迁库）、密码找回/修改、多租户 UI（tenant_id 仅预留）、MCP tools（identity 不向 AI 暴露任何工具；MCP 鉴权中间件归 M4）。

## 2. 数据模型

通用：除 `tenants` 用 `IdTimestampMixin`（id/created_at/updated_at）外，其余表均用 `EntityMixin`（+ `tenant_id`，去掉现有 `"default"` 默认值，service 显式传入）。id 为 uuid hex `String(32)`；时间一律 `TIMESTAMP(timezone=True)` UTC；枚举 DB 存字符串。

| 模型 | 关键字段 | 说明 |
| --- | --- | --- |
| Tenant | `name String(200)`、`slug String(64) UNIQUE` | setup 创建 "Default Workspace"（slug `default`）；存在行即视为 setup 已封禁 |
| User | `email String(255)`（service 统一小写，**UNIQUE(tenant_id, email)**）、`display_name String(100)`、`avatar_url String(500)?`、`password_hash String(255)?`（bcrypt）、`identity_provider = local\|multirag\|oidc`（默认 local）、`external_user_id String(64)?`（索引；multirag `User.id` 为 uuid 字符串，String(64) 足够）、`status = active\|invited\|disabled`、`last_login_at?` | |
| Session | `user_id FK users CASCADE`（索引）、`token_hash String(64) UNIQUE`（sha256 hex）、`ip_address String(45)?`、`user_agent String(400)?`、`expires_at`（索引）、`revoked_at?`、`last_seen_at?` | 明文 token `wn_sess_` + `secrets.token_urlsafe(32)`，仅 Set-Cookie 一次，DB 只存 hash |
| InviteToken | `token_hash String(64) UNIQUE`、`email String(255)`、`created_by FK users`、`tenant_role String?`（v0.1 仅 `admin`）、`project_id FK projects?`、`project_role String?`（project_admin\|member\|viewer）、`expires_at`、`accepted_at?`、`accepted_user_id FK users?`、`revoked_at?` | **CHECK：`(tenant_role IS NULL) != (project_id IS NULL)`**（tenant 授权与项目授权二选一）；部分唯一索引 `UNIQUE(tenant_id, email) WHERE accepted_at IS NULL AND revoked_at IS NULL`（一邮箱一个待处理邀请） |
| Project（modules/projects，M1 仅模型） | `name String(200)`、`key String(20)`（**UNIQUE(tenant_id, key)**）、`description Text?`、`status = active\|archived`、`owner_id FK users?`、`settings JSONB {}`、`created_by?`、`updated_by?` | setup 种子默认项目需要；M1 仅 `models.py` + `create_project()` service 函数，CRUD 归 M2 |
| ProjectMember | `project_id FK projects CASCADE`、`user_id FK users CASCADE`（索引）、`role = project_admin\|member\|viewer`、`created_by`、**UNIQUE(project_id, user_id)** | 用户的项目成员资格与项目角色的**唯一**存放处（D3） |
| RoleBinding | `subject_type = user\|ai_agent`、`subject_id String(32)`、`role`（6 角色枚举）、`scope_type = tenant\|project`、`scope_id String(32)?`（tenant 级为 NULL）、`created_by?`、UNIQUE 全列（nulls not distinct）、索引 `(subject_type, subject_id)` | **CHECK：`NOT (subject_type='user' AND scope_type='project')`**——用户的项目角色禁止写这张表（D3 禁双写的数据库级保障）；用途：tenant 级 owner/admin、AI Agent 授权 |
| AIAgent | `name String(100)`（UNIQUE(tenant_id, name)）、`description Text?`、`status = active\|disabled`、`external_agent_id String(64)?`（multirag agent id 即 `UserCanvas.id`（uuid 字符串），v0.1 取自 .env）、`created_by?` | setup 种子 "WorkNexus Assistant" |
| McpDelegationToken | `token_hash String(64) UNIQUE`、`user_id FK users`、`agent_id FK ai_agents`、`project_id FK projects?`、`conversation_id String(64)?`、`run_id String(64)?`（M5 表未建，纯字符串无 FK）、`permissions_snapshot JSONB`、`expires_at`（索引）、`revoked_at?`、`last_used_at?` | 明文 `wn_del_` + token_urlsafe(32)；TTL 5–10 分钟（配置）；TTL 内可重复使用（D5 不强制 one-time） |
| AuditLog（modules/audit） | `actor_type = user\|ai_agent\|system`、`actor_id?`、`action String(100)`（如 `auth.login`）、`resource_type String(50)`、`resource_id String(64)?`、`project_id?`（无 FK，索引）、`before JSONB?`、`after JSONB?`、`detail JSONB?`（不叫 metadata，避撞 `Base.metadata`）、`request_id String(36)?`、`ip_address String(45)?` | 索引：`(tenant_id, created_at)`、`(resource_type, resource_id)`、`(actor_type, actor_id)`、`action`；M5 再加 AI 链路列（requested_by/agent_id/approved_by/skill_invocation_id），此前用 `detail` 承载 |

哈希策略：**bcrypt 仅用于密码**（低熵）；session/invite/delegation token 为高熵随机串，DB 存 **sha256 hex**（避免每请求 ~100ms bcrypt 开销）。bcrypt 用 `bcrypt` 包直用（不引 passlib，已停止维护且与 bcrypt 4+ 不兼容）。

新增配置（`WORKNEXUS_` 前缀）：`session_cookie_name="worknexus_session"`、`session_ttl_days=7`、`delegation_token_ttl_seconds=600`（校验范围 300–600）、`bcrypt_rounds=12`（测试覆盖为 4）、`invite_ttl_days=7`。

## 3. REST API

身份模块错误码占 **4xxx** 段（`core/errors.py`）：

| 码 | 名 | 触发 |
| --- | --- | --- |
| 4001 | SETUP_ALREADY_COMPLETED | setup 封禁后再 POST |
| 4002 | INVALID_CREDENTIALS | 登录账号或密码错误（200+code，不暴露具体哪项错） |
| 4003 | USER_DISABLED | 禁用用户登录 |
| 4004 | EMAIL_ALREADY_EXISTS | 邀请已注册邮箱 / 接受时撞已有用户 |
| 4005 | INVITE_NOT_FOUND | 邀请 token 无效 |
| 4006 | INVITE_EXPIRED | |
| 4007 | INVITE_ALREADY_ACCEPTED | |
| 4008 | INVITE_REVOKED | |
| 4009 | DELEGATION_TOKEN_INVALID | |
| 4010 | DELEGATION_TOKEN_EXPIRED | |
| 4011 | CANNOT_MODIFY_OWNER | admin 试图变更 owner 的绑定/状态 |
| 4012 | PASSWORD_TOO_WEAK | 密码 < 8 字符（前端 zod 同步校验） |

HTTP 语义：未认证（无/无效 cookie）→ 401；权限不足 → 403；其余业务错误 → 200 + 非 0 code（含登录失败 4002）。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/setup/status` | `{ initialized: bool }` | 公开 |
| POST | `/api/v1/setup` | 首启初始化（见下方流程），成功后**自动登录**（种 cookie）并返回 CurrentUserContext | 公开（封禁后 4001） |
| POST | `/api/v1/auth/login` | 邮箱+密码登录，Set-Cookie | 公开 |
| POST | `/api/v1/auth/logout` | 撤销当前 session + 清 cookie | 已登录 |
| GET | `/api/v1/me` | CurrentUserContext | 已登录 |
| GET | `/api/v1/users` | 用户列表（`Page[UserOut]`，page/page_size） | `user.read` |
| POST | `/api/v1/invites` | 创建邀请；**明文 token 仅此响应返回一次**，前端拼 `/invites/{token}` 链接 | `user.invite` |
| GET | `/api/v1/invites` | 邀请列表（状态：pending/accepted/expired/revoked，不含明文 token） | `user.invite` |
| POST | `/api/v1/invites/{invite_id}/revoke` | 撤销待处理邀请 | `user.invite` |
| GET | `/api/v1/invites/{token}` | 激活页预览：email、目标角色/项目、状态 | 公开 |
| POST | `/api/v1/invites/{token}/accept` | 设置 display_name + 密码激活，写入 project_members **或** role_bindings（二选一），成功后**自动登录** | 公开 |

> `GET /api/v1/invites` 与 `POST /invites/{id}/revoke` 为规格书 §1 之外新增（members 页需要），已经用户确认纳入 M1。

**响应字段约定（全项目，新 5.6 手册条目）**：响应 schema 继承 `core/schemas.py` 的 `ApiModel`（`alias_generator=to_camel`，`populate_by_name=True`），JSON 输出统一 camelCase；orval 生成类型自动跟随。

**CurrentUserContext**（`GET /api/v1/me`）：

```jsonc
{
  "user": { "id", "email", "displayName", "avatarUrl", "identityProvider", "externalUserId" },
  "tenant": { "id", "name", "slug" },
  "roles": ["owner"],                       // tenant 级角色（role_bindings）
  "permissions": ["user.read", "..."],      // tenant 级权限并集
  "projects": [{ "id", "name", "role", "permissions": ["..."] }],  // 有 project.read 的项目；owner/admin 为全部 active 项目，role 显示其 tenant 角色
  "ai": { "availableAgents": [{ "id", "name", "status" }] }
}
```

### Setup 流程（单事务）

1. `pg_advisory_xact_lock`（常量 key）→ 复查 `tenants` 无行（有 → 4001）
2. 建 Tenant（name 取请求，默认 "Default Workspace"，slug `default`）
3. 建 owner User（email/display_name/password，bcrypt，status=active，identity_provider=local）
4. `role_bindings(user, owner, scope=tenant)` —— **不写 project_members**：tenant 角色对所有项目全局生效
5. `projects.create_project("WorkNexus Internal", key="WNX", owner_id=owner)`
6. 建 AIAgent("WorkNexus Assistant"，external_agent_id 取 .env）+ `role_bindings(ai_agent, ai_agent, scope=tenant)`
7. `audit.record("setup.complete")`（system actor，同事务）
8. 建 session、Set-Cookie、返回 CurrentUserContext

### 会话机制（D2）

- Cookie：`worknexus_session`，HttpOnly、SameSite=Lax、Path=/、Max-Age 7 天、Secure 仅 prod。dev 下 `localhost:5173 → localhost:8200` 同站，Lax 正常携带；CORS 已 `allow_credentials=True`。
- `get_current_actor`（`core/deps.py` 真实现，替换 dev-user 桩，不留开发期后门）：cookie → sha256 → 查 sessions（未撤销、未过期、join status=active 用户）→ `Actor(id, type=USER, tenant_id)`；任何无效 → 401。`last_seen_at` 距上次超 5 分钟才回写（避免每请求写库）。
- 登录流程：lower(email) → 查用户（status 校验 4003）→ `bcrypt.checkpw`（失败 4002）→ 建 session（记 ip/user_agent）→ Set-Cookie → 更新 `last_login_at` → `audit.record("auth.login")`。
- 登出：当前 session `revoked_at` → 清 cookie → `audit.record("auth.logout")`。

### 邀请流程

- 创建（`user.invite`）：校验邮箱非既有用户（4004）、无待处理邀请 → 生成 `wn_inv_` token → 存 hash + 授权目标（tenant_role **XOR** project_id+project_role）→ `audit.record("invite.create")` → 返回 `{ inviteId, token, expiresAt }`。
- 接受（公开，单事务）：按 hash 查（4005/4006/4007/4008）→ 建 User（display_name+密码，status=active）→ 按邀请目标写 `project_members` 或 `role_bindings`（**绝不双写**）→ 标记 accepted → 审计 `invite.accept` + `project.member.add` 或 `role_binding.create` → 自动登录。

### Delegation token（D5，仅 service 函数，无 REST 端点）

```python
async def issue_delegation_token(
    db, actor, *, user_id, agent_id,
    project_id=None, conversation_id=None, run_id=None,
) -> IssuedDelegationToken  # { token: "wn_del_..."（仅此一次明文）, expires_at }

async def verify_delegation_token(db, token) -> DelegationContext
# DelegationContext: tenant_id/user_id/agent_id/project_id/conversation_id/run_id/permissions_snapshot
```

- issue：校验 user 与 agent 均 active → `permissions_snapshot = { user: [...], agent: [...], effective: 交集（按 scope）}` 经 `core/access` 计算 → TTL 取配置 → 存 hash。
- verify：sha256 查找；未知/撤销 → 4009，过期 → 4010；回写 `last_used_at`；TTL 内可重复使用。
- 明文 token 不落日志、不进审计明文、不进 SkillInvocation input。消费方：M5 签发、M4 MCP 中间件校验。
- 链路可行性已对 multirag 源码核实：completions 请求体含 `custom_header` 字段（`api/apps/sdk/session.py`），经 `canvas.py` 注入组件参数并由 `common/mcp_tool_call_conn.py` 透传到 MCP 调用；MCPServer 配置另有 `headers` JSONB（存 server token，M4 用）。multirag 侧 APIToken 为 Bearer、tenant 级粒度，与 D7 一致。

## 4. MCP Tools

**无。** identity 不向 AI 暴露任何工具（登录/邀请/授权没有 AI 调用场景，且 high_write 类操作 v0.1 禁止 AI 执行）。`/mcp` 双 token 校验中间件归 M4，依赖本模块的 `verify_delegation_token`。

## 5. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/setup` | 首启初始化（GuestOnly） | 工作区名 + owner 邮箱/名称/密码；成功自动登录进 AppShell；已初始化则重定向 /login |
| `/login` | 登录（GuestOnly） | 邮箱+密码，react-hook-form + zod；失败 toast（4002/4003 文案） |
| `/invites/:token` | 邀请激活（公开） | 预览邀请信息 → 设 display_name + 密码 → 激活并自动登录 |
| `/settings/members` | 成员管理（AppShell 内） | 用户列表（DataTable）+ 创建邀请 Dialog（PermissionGate `user.invite`）+ 复制邀请链接 + 撤销邀请（ConfirmDialog） |
| AppShell 顶栏 | 用户菜单 | 头像+displayName，DropdownMenu：登出 |

前端架构要点：

- **无 zustand auth store**：会话在 HttpOnly cookie，`/me` 是服务器状态，归 TanStack Query（`lib/auth/use-me-query.ts`）。
- `lib/auth/`（features 禁互 import，故下沉）：`keys.ts`、`use-me-query.ts`（401 不重试）、`use-setup-status-query.ts`、`permission.tsx`（`useHasPermission(perm, projectId?)` + `PermissionGate`）。
- 路由守卫：`RequireAuth`（布局路由：pending→PageSkeleton；未初始化→/setup；401→/login 带 state.from）+ `GuestOnly`（已登录→/；/setup 已初始化→/login）。
- mutator 改造：`packages/contracts/src/mutator.ts` 与 `lib/api-client.ts` 加 `credentials: 'include'`；`lib/query-client.ts` 捕获 401 → 失效 me query → 守卫重定向。
- 新建 patterns（+5.5 手册条目）：`page-skeleton`、`empty-state`、`error-state`、`confirm-dialog`、最小 `data-table`（@tanstack/react-table + columns.tsx 模式）。
- 新增 shadcn 组件（单独 commit）：form/input/label/card/avatar/dropdown-menu/dialog/alert-dialog/skeleton/table/badge。

i18n namespace：`auth`、`settings`（zh-CN / en-US 同步提供）；`common` 增 userMenu/nav 词条。

## 6. 审计与权限点

### 审计事件（M1，action 常量）

`setup.complete`、`auth.login`、`auth.logout`、`invite.create`、`invite.revoke`、`invite.accept`、`role_binding.create`、`role_binding.delete`、`project.member.add`（成员变更其余动作归 M2，常量先定）。`audit.record()` 只 add 不 commit，与业务写入同事务；`request_id` 自 `core/request_id.py` contextvar 读取。

### 权限点与 6 角色矩阵（v0.1 全量，一次定死，`core/access.py` 代码常量）

✓=授予；project_admin/member/viewer 为项目角色，仅在其项目内生效；owner/admin 为 tenant 角色，**全局生效、无需 project_members 行**；ai_agent 列是能力上限（caps），实际写入永远再过 D5 双重校验（用户∧Agent∧资源∧风险∧确认），且 high_write 类权限点对 AI 全部不授予。

| 权限点 | owner | admin | project_admin | member | viewer | ai_agent |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| tenant.manage | ✓ | | | | | |
| user.read | ✓ | ✓ | ✓ | ✓ | ✓ | |
| user.invite | ✓ | ✓ | | | | |
| user.manage | ✓ | ✓ | | | | |
| role.assign | ✓ | ✓ | | | | |
| ai_agent.read | ✓ | ✓ | ✓ | ✓ | ✓ | |
| ai_agent.manage | ✓ | ✓ | | | | |
| audit.read | ✓ | ✓ | | | | |
| project.create | ✓ | ✓ | | | | |
| project.read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| project.update | ✓ | ✓ | ✓ | | | |
| project.archive | ✓ | ✓ | ✓ | | | |
| project.member.manage | ✓ | ✓ | ✓ | | | |
| work_item.read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| work_item.create | ✓ | ✓ | ✓ | ✓ | | ✓ |
| work_item.update | ✓ | ✓ | ✓ | ✓ | | ✓ |
| work_item.delete | ✓ | ✓ | ✓ | | | |
| work_item.transition | ✓ | ✓ | ✓ | ✓ | | ✓ |
| work_item.comment | ✓ | ✓ | ✓ | ✓ | | ✓ |
| work_item.assign | ✓ | ✓ | ✓ | ✓ | | ✓ |
| skill.read | ✓ | ✓ | ✓ | ✓ | ✓ | |
| skill.invoke | | | | | | ✓ |
| workchat.use | ✓ | ✓ | ✓ | ✓ | | |
| agent_action.confirm | ✓ | ✓ | ✓ | ✓ | | |
| intake.read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| intake.create | ✓ | ✓ | ✓ | ✓ | | ✓ |
| intake.triage | ✓ | ✓ | ✓ | | | ✓* |
| dashboard.read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

\* intake.triage 的 AI 授予仅经确认后的 AgentAction 生效（accept/reject 属 low_write 确认流）。其他说明：owner 与 admin 仅差 `tenant.manage`；"admin 不能动 owner"（4011）是 service 规则不是矩阵项；`project.create` v0.1 仅 owner/admin（member 自建项目 v0.2+ 再议）。

### `core/access.py` 设计

```python
class Role(StrEnum): ...        # 6 角色
class Permission(StrEnum): ...  # 上表全量权限点
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]]

class Scope(BaseModel):   # type: tenant|project, project_id?
class Subject(BaseModel): # actor + tenant_roles: list[Role] + project_roles: dict[project_id, Role]

async def load_subject(db, actor) -> Subject
#   user: tenant_roles ← role_bindings(scope=tenant)；project_roles ← project_members
#   ai_agent: 全部 ← role_bindings

def can(subject, action: Permission, scope: Scope | None = None) -> bool
#   1) tenant 角色权限并集（全局生效）
#   2) scope 为 None/tenant：查并集
#   3) scope 为 project：并集 ∪ ROLE_PERMISSIONS[project_roles[project_id]] 后查

def require_permission(action, *, project_param: str | None = None)  # FastAPI 依赖工厂，返回 Subject，失败 403
async def get_current_subject(...)  # get_current_actor + load_subject，request.state 缓存
```

路由层禁止散落角色 if 判断；前端只消费 `/me` 的 permissions，不自行推导。

## 7. 测试点

- **后端 fixtures（首个 `tests/conftest.py`）**：session 级 engine（`WORKNEXUS_TEST_DATABASE_URL`，drop_all/create_all 一次）；function 级事务回滚 db（`join_transaction_mode="create_savepoint"`）；`httpx.AsyncClient(ASGITransport)` + `dependency_overrides[get_db]`；settings 覆盖 `bcrypt_rounds=4`；域 fixture：`initialized_tenant`、`owner_client`、`member_user`。
- **p0**：`can()` 矩阵真值表（纯函数）；setup 主路径 + 封禁（4001）；登录种 HttpOnly cookie + `/me` 返回完整上下文；未认证 `/me` → 401。
- **p1 service**：错密码 4002 / 禁用 4003；会话过期与撤销；邀请创建/接受/过期/撤销/重复邮箱；接受写 project_members XOR role_bindings；RoleBinding CHECK 防双写；delegation 签发/校验/过期/快照内容；审计与业务同事务（回滚则双消失）。
- **p1 router**：member POST /invites → 403；Envelope 形状；cookie 属性（HttpOnly/SameSite=Lax/Max-Age）；登出后旧 cookie 401。
- **p2**：`last_seen_at` 节流；/users 分页；`alembic upgrade head` 冒烟。
- **前端（vitest + msw）**：useMeQuery / login mutation；RequireAuth 401 与未初始化重定向；login 表单 zod 校验；patterns 组件渲染。
- **E2E（Playwright，`apps/web/e2e/auth.spec.ts`）**：对 DB 状态幂等——`/setup/status` 未初始化则走 /setup 建 owner，否则固定 E2E 账号 /login；断言 AppShell + 用户菜单 displayName；登出回 /login。webServer 自动起 uvicorn:8200 + vite:5173；PostgreSQL 为文档化前置（`infra/docker` compose）。

## 8. 参考实现对照（Plane，/Users/dxl/project/ts/plane）

设计时对照了 Plane 的 IAM 实现，以下差异为**有意为之**（非疏漏）：

| 维度 | Plane | WorkNexus（本设计） | 理由 |
| --- | --- | --- | --- |
| 角色模型 | 数字角色（Admin=20/Member=15/Guest=5），权限判断用 `role >= N` 阈值比较 | 命名角色 + 显式权限点矩阵 | D3 已定；AI 参与场景需要细粒度权限点（AI caps、风险分级），阈值比较表达不了 |
| tenant 管理员的项目访问 | workspace admin 改项目仍需自己是 ProjectMember | owner/admin tenant 角色全局生效，无需 project_members 行 | 简化 v0.1；避免 setup 给 owner 建成员行、邀请 admin 后逐项目补行 |
| 邀请 token | JWT（HS256 签 email+timestamp），无过期时间，明文存库 | 不透明随机串 + sha256 落库 + TTL 7 天 | 可撤销、可过期、库泄露不可用，安全性更强 |
| 会话存储 | Django DB session，session_key 明文为主键 | 自建 sessions 表，DB 只存 sha256 hash | D2 已定 |
| API token（机器身份） | `plane_api_`+uuid 明文存库、`last_used`、bot user 模式 | delegation token 短 TTL + hash + 权限快照；长期 server token 走 .env（M4） | AI 身份穿透需要"代表谁"的短期凭据，非长期 PAT |
| 密码强度 | zxcvbn score ≥ 3 | 最小 8 位（zod + 后端 4012） | v0.1 从简；zxcvbn 类强度校验列为后续增强 |
| IAM 审计 | 无成员/认证专门审计表（只有 IssueActivity） | audit_logs 横切，登录/邀请/绑定全记 | 本产品核心诉求（AI 安全参与），审计不可省 |

借鉴吸收：sessions 记录 ip/user_agent/last_seen（对应 Plane device_info）；7 天 cookie 同其默认；members 页"列表+邀请+撤销"交互范围与其 workspace members 页对齐。

## 9. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-12 | （设计） | 初版设计：表结构、4xxx 错误码、权限矩阵全量定死、camelCase ApiModel 约定、session/邀请/delegation 细节、3 PR 拆分；对照 Plane IAM 实现并核实 multirag custom_header 透传链路 |
| 2026-06-13 | PR2 | 权限与身份接口落地：`core/access.py` 完整版（Subject/load_subject/permissions_for/can/require_permission/get_current_subject，request.state 缓存）；`core/pagination.py` `Page[T]` + page/page_size 查询参数（响应 camelCase `pageSize`，AGENTS/CLAUDE §4.3 已注）；`GET /me`、`GET /users`（user.read + 分页）、邀请五端点（create/list/revoke/公开 preview/公开 accept，accept 写 project_members XOR role_bindings + 自动登录）；delegation token issue/verify service（快照含 user/agent/effective 交集，TTL 内可重用）；25 个新测试（403 矩阵抽查、邀请全生命周期、delegation、alembic 升级冒烟）累计 57 个全绿。补 PR1 遗留的 alembic p2 冒烟测试 |
| 2026-06-12 | PR1 | 后端地基落地：10 表模型 + 初始迁移（含 role_bindings 防双写 CHECK、邀请 XOR CHECK、部分唯一索引）；`core/access.py` 角色×权限矩阵常量；`core/schemas.py` ApiModel（camelCase，5.6 手册同步）；`core/request_id.py` 中间件；setup（advisory lock + 封禁 + 种子数据 + 自动登录）、登录/登出、session 解析（`get_current_actor` 真实现，dev-user 桩删除）；audit.record 同事务写入；conftest 测试地基（真实 PG + savepoint 回滚 + ASGI client）+ 32 个测试；AGENTS/CLAUDE §4.1 模块名 users→identity、ActorType `ai`→`ai_agent`。注：ApiModel 与 CurrentUserContext 构建提前到 PR1（setup/login 响应需要），原计划在 PR2；alembic upgrade p2 冒烟测试推迟到 PR2 |
