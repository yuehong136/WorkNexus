# 模块：settings（Settings Lite / 设置中心）

> 状态：设计中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/settings`
> 关联 module（后端）：`apps/server/src/worknexus/modules/settings`（仅 AI 连接只读端点）+ `identity`（PATCH /me）

## 1. 目标与范围

把现有 `features/settings`（仅 `members` 单页）扩成多页 **Settings Lite**，并补两个极小后端端点。四块（spec §9）：

1. **个人资料**：展示 + **可改显示名**；退出登录（已有 `UserMenu`）。
2. **项目入口**：只读列出我的项目 + 链到既有项目详情/成员（无新后端）。
3. **AI 连接**：multirag endpoint / 默认 agent_id / client / timeout / APIToken —— **`.env` 驱动只读脱敏展示**（绝不回明文 token）。
4. **Skills**：**只读展示「执行策略」**——注册 Skill + tool 风险等级 + 策略文案（read=直接执行 / low_write=需 AgentAction 确认 / high_write=v0.1 禁止）。复用 `GET /skills`。

边界：除「改显示名」一处小写动作外，全部只读。**不建表、不迁移、不暴露 MCP**。

### 本期与用户敲定的关键设计抉择（A–G）

| 点 | 决策 |
| --- | --- |
| **A 个人资料可写性** | **仅可改显示名**。`display_name` 是 `users` 现有字段、`/me` 已返回，无需新表/不改身份模型。新增 `PATCH /api/v1/me`（仅 `displayName`，本人改自己），写审计，返回更新后 `CurrentUserContext`。email/角色/身份来源/头像**只读**。**改密码后置**（需校验当前密码 / bcrypt 重哈希 / 是否撤销其他 session / provider 是否允许本地改密 → 独立安全设置 PR，不进 M8）。头像无上传链路（无对象存储）→ 只展示。 |
| **B AI 连接** | **只读脱敏端点** `GET /api/v1/settings/ai-connection`，从 `config.py`（`get_settings()`）读。**绝不回明文** `api_key`：只回 `apiKeyConfigured: bool` + `apiKeyMasked`（尾 4 位形如 `••••1234`，未配置则 None）。落库可配后置（D7：v0.1 以 .env 为准）。 |
| **C Skill 开关** | **不做真实启停开关、不建 `skill_enablement` 表**。M8 Settings 的 Skill 区域 = **只读「执行策略」展示**（复用 `GET /skills` 的 `SkillOut`/`SkillToolOut`：tool 风险等级 + `executableInV01`）。真实启停（表 + 迁移 + `skill.manage` 权限 + 写端点 + 接入 `SkillInvocationMiddleware` 调用前门禁 + disabled 调用如何记 skill_invocation/audit + contracts）是**新的安全控制能力**，后置为独立设计点，**不在 M8 做「假开关」**（UI 放 toggle 但不接真实门禁是最差方案，破坏 AI 安全承诺）。 |
| **D 权限** | 全部复用现有点，**不改 access.py**。Profile 改 = 本人（`get_current_actor`）；AI 连接只读 = `ai_agent.manage`（admin/owner，member 不能看系统 AI 配置）；Skill 展示 = `skill.read`（viewer+）；项目入口 = `project.read`；成员 = `user.read`（现状）。 |
| **E 审计** | **改显示名写审计**：新增 `AuditAction.USER_PROFILE_UPDATE = "user.profile.update"`（StrEnum，无迁移），`record(action=USER_PROFILE_UPDATE, resource_type="user", resource_id=actor.id, before={displayName}, after={displayName})` 与写库同事务。AI 连接/Skill 只读**不审计**。 |
| **F 错误码/表/迁移** | **无新错误码**（显示名校验经 Pydantic schema 约束 min/max length，对齐 setup/invite 口径；8xxx 仍空闲）；**无新表、无迁移**（仅加一个 `AuditAction` 枚举值；`alembic check` 应无漂移）。 |
| **G 后端模块归属** | `PATCH /me` 放 **identity**（改 User，属身份域）；AI 连接只读端点放**新建极小 `modules/settings`**（系统设置域，清晰边界，未来可扩）。 |

### 明确不做 / 推迟

- 改密码 / 安全设置（撤销 session、2FA） → 独立安全 PR。
- 头像上传 / 对象存储 → 推迟。
- 真实 Skill 启停开关 + `skill_enablement` 表 + `skill.manage` 权限 → 独立设计点后置。
- AI 连接落库可配（写动作 + 凭证加密存储） → 后置（v0.1 以 .env 为准）。
- 工作项类型/状态/优先级配置（v0.1 固定）→ 已在 spec §9 标注不做。

## 2. 数据模型

**本模块不新建任何表、无模型变更、无 Alembic 迁移。** 唯一持久化变更是改本人 `users.display_name`（既有列）。读 `config.py` 的 AI 设置（非 DB）。

| 既有资源 | 用途 |
| --- | --- |
| `users.display_name`（identity） | Profile 改显示名（本人） |
| `config.py` `Settings`（`get_settings()`） | AI 连接只读脱敏：`ai_client` / `ai_platform_base_url` / `ai_platform_default_agent_id` / `ai_platform_timeout_seconds` / `ai_platform_api_key`(脱敏) / `intake_triage_provider` / `dashboard_insights_provider` |
| MCP 组合层（反射，`service.list_skills`） | Skill 执行策略只读展示 |

## 3. REST API

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| PATCH | `/api/v1/me` | 改本人显示名，返回更新后 `CurrentUserContext` | 登录（本人，`get_current_actor`） |
| GET | `/api/v1/settings/ai-connection` | AI 连接脱敏只读 | `ai_agent.manage`（admin/owner） |
| GET | `/api/v1/skills`（既有，M4） | Skill 执行策略只读（settings Skill 区复用） | `skill.read`（viewer+） |

### schema

```text
# identity/schemas.py
ProfileUpdateIn   { displayName: str }          # Field(min_length=1, max_length=N) 对齐 setup/invite
# PATCH /me 返回既有 CurrentUserContext（与 GET /me 同构）

# modules/settings/schemas.py
AiConnectionOut   { aiClient: str, aiPlatformBaseUrl: str, aiPlatformDefaultAgentId: str,
                    aiPlatformTimeoutSeconds: float,
                    apiKeyConfigured: bool, apiKeyMasked: str | None,    # 绝不回明文
                    intakeTriageProvider: str, dashboardInsightsProvider: str }
```

### service

- `identity.service.update_profile(db, actor, data: ProfileUpdateIn) -> CurrentUserContext`：取本人 `User`、改 `display_name`、`audit.record(USER_PROFILE_UPDATE, resource_type="user", resource_id=actor.id, before/after)`、`build_current_user_context`。同事务。
- `settings.service.get_ai_connection(settings: Settings) -> AiConnectionOut`：从 `get_settings()` 读，`apiKeyMasked = mask(ai_platform_api_key)`（空→`apiKeyConfigured=False, apiKeyMasked=None`；非空→只露尾 4 位）。纯读、无 audit。

router：`PATCH /me` 在 identity router（`operation_id="update_me"`，依赖 `get_current_actor`）；`GET /settings/ai-connection` 在新 `settings` router（`require_permission(Permission.AI_AGENT_MANAGE)`），`api.py` 注册 settings_router 一行。

## 4. MCP Tools

**无。** 设置不暴露给 AI。

## 5. UI / 页面

把 `features/settings` 由单页扩为带左侧 sub-nav 的布局（参考 Plane settings sidebar IA）。

| 路由 | 页面 | 关键交互 / 权限 |
| --- | --- | --- |
| `/settings`（重定向 `/settings/profile`） | 设置布局 | `settings-layout.tsx`：左侧 sub-nav（各项 `PermissionGate` 门禁）+ 右侧 `<Outlet />` |
| `/settings/profile` | 个人资料 | react-hook-form + `zodResolver` 改 `displayName`（schema 放 `api/schemas.ts`）→ `useUpdateProfileMutation`(PATCH /me) 成功 invalidate me query；email/角色/身份来源/头像只读；本人可见 |
| `/settings/projects` | 项目入口 | 只读列我的项目（`/me` projects）+ 链项目详情/成员；`project.read` |
| `/settings/ai` | AI 连接 | `useAiConnectionQuery` 脱敏只读卡；`ai_agent.manage` 门禁 |
| `/settings/skills` | Skill 执行策略 | `useSkillsQuery`（contracts `listSkills`）只读：每 skill tools + 风险等级 Badge + 策略文案；`skill.read` |
| `/settings/members`（现有） | 成员 | 保留；`user.read` |

- `lib/paths.ts` 加 `settingsProfile/settingsProjects/settingsAi/settingsSkills`（保留 `settingsMembers`）。
- app-shell：把单一「成员」入口改为「设置」入口（指向 `/settings`）。
- `features/settings/api/`：`useUpdateProfileMutation`（成功 invalidate `me` query，错误经全局 `onError` toast 或表单内联）、`useAiConnectionQuery`、`useSkillsQuery`（复用 contracts `listSkills`，共享 client 非 feature 互 import）。
- 跨 feature 约束：settings 不 import `features/skills`；Skill 执行策略页自查 `listSkills` 并用 `patterns/DataTable` 渲染（settings 视角的只读策略表，区别于 `/skills` 中心页）。

i18n namespace：扩展现有 `settings`（profile / ai / skills / 导航 子键）；zh-CN / en-US 同步，禁硬编码、禁裸色值。

## 6. 审计与权限点

### 审计事件

- **改显示名**：`AuditAction.USER_PROFILE_UPDATE`（`resource_type="user"`，`resource_id=actor.id`，before/after 含 displayName），与写库同事务。
- AI 连接只读 / Skill 展示 / 项目入口 → **不审计**（纯读）。

### 权限点（沿用 M1，禁改 access.py）

- Profile 改：本人（`get_current_actor`，无权限点）。
- AI 连接只读：`ai_agent.manage`（admin/owner；member 不能看系统 AI 配置 → 满足 spec §9 验收）。
- Skill 展示：`skill.read`（viewer+）。
- 项目入口：`project.read`；成员：`user.read`（现状）。
- 不新增权限点 → 不改 access.py → 不触发 contracts 连锁。

## 7. 测试点

- **service 单测**：`update_profile` 改 display_name + 写一行 `USER_PROFILE_UPDATE` 审计（before/after 正确）；`get_ai_connection` **明文 key 永不出现在返回**（`apiKeyMasked` 仅尾 4 位 / 未配置为 None）。
- **REST**：`PATCH /me` 本人改成功返回更新后 CurrentUserContext、未登录 401、显示名空/超长 422；`GET /settings/ai-connection` admin/owner 可读、member 403、未登录 401。
- **前端（vitest + msw）**：profile 表单（zod 校验 + 提交 invalidate me）；`useAiConnectionQuery` 脱敏渲染；Skill 策略表渲染。
- **E2E（Playwright 主链路）**：设置页脱敏展示 AI 连接（无明文）——并入 home/E2E PR；改显示名后 `/me` 刷新（可选）。
- 覆盖率门槛：后端 service ≥85% / 整体 ≥70%；前端 `lib/` + stores ≥80%。

## 8. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-16 | PR3（前端多页） | `features/settings` 由单成员页扩为带左侧 sub-nav 的布局：`settings-layout.tsx`（NavLink + `PermissionGate` 各项门禁 + `<Outlet/>`，`/settings` index `<Navigate>` 重定向 `/settings/profile`）；`profile-page.tsx`（react-hook-form + `zodResolver` 改 displayName → `useUpdateProfileMutation`〔PATCH /me + invalidate me query + setQueryData〕；email/角色/身份来源只读）；`projects-settings-page.tsx`（只读列 `/me` 项目 + Badge 角色 + 链项目详情）；`ai-connection-page.tsx`（`useAiConnectionQuery` 脱敏只读卡，gated `ai_agent.manage`，apiKeyMasked 仅尾4位）；`skills-settings-page.tsx`（`useSkillCatalogQuery` 复用 contracts `listSkills` 自查〔非 feature 互 import〕，只读「执行策略」：tool 风险 Badge + 策略文案 read=直接执行/low_write=需确认/high_write=禁止）；保留 `members-page` 移入布局。`schemas.profileSchema` + `keys` 加 aiConnection/skillCatalog。`paths.settings*` + router 嵌套布局懒加载 + app-shell 「成员」入口改「设置」入口（指向 `/settings`，主导航不再门禁、子页各自门禁）。i18n `settings` namespace 扩 title/nav/profile/projects/ai/skills（zh/en `satisfies` 对齐）。vitest +1（`useAiConnectionQuery` 脱敏 unwrap，msw）；web lint(0 err)/typecheck/test(33)/build 全绿。 |
| 2026-06-16 | PR2（后端端点） | **identity**：`ProfileUpdateIn{displayName: Field(1..100)}`；`service.update_profile`（改本人 display_name + `AuditAction.USER_PROFILE_UPDATE` 审计 before/after + commit + 返回 `CurrentUserContext`）；`PATCH /api/v1/me`（`get_current_actor` 本人，`operation_id=update_me`）。**新建 `modules/settings`**：`AiConnectionOut`（aiClient/baseUrl/defaultAgentId/timeout/`apiKeyConfigured`/`apiKeyMasked` 尾4位/triage·insights provider，**绝不含明文 key**）；`service.get_ai_connection(settings)` 纯读脱敏；`GET /api/v1/settings/ai-connection`（`require_permission(AI_AGENT_MANAGE)` admin/owner）；`api.py` 注册。新增 `AuditAction.USER_PROFILE_UPDATE`（枚举值，无迁移）。测试 +10（settings service 3：脱敏·明文永不出现·非密字段透传；settings API 3：owner 读·member 403·401；profile 4：改名持久化·写审计 before/after·空名 422·401）；全套 254 passed，ruff/mypy 全绿，alembic check 无漂移。无新表/迁移/MCP。 |
| 2026-06-16 | PR1（设计） | 初版设计：与用户敲定 A–G（A 个人资料仅可改显示名〔PATCH /me + 审计〕、改密码/头像后置；B AI 连接只读脱敏端点绝不回明文 key；C 不做真实 Skill 开关/不建 enablement 表、只读「执行策略」展示、真实启停后置；D 全复用权限不改 access.py〔profile=本人·ai 连接=ai_agent.manage·skill 展示=skill.read〕；E 改显示名写 USER_PROFILE_UPDATE 审计、只读不审计；F 无新错误码·无表无迁移仅加枚举值；G PATCH /me 归 identity、AI 连接归新 settings 模块）；`ProfileUpdateIn`/`AiConnectionOut` schema 定型；settings 多页 sub-nav IA 定型；同步 roadmap M8 进度 |
