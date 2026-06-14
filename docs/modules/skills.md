# 模块：skills（Skills / MCP 安全骨架）

> 状态：开发中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/skills`
> 关联 module（后端）：`apps/server/src/worknexus/modules/skills`

## 1. 目标与范围

M4 在 M1（身份/权限/delegation token）、M3（`/mcp` 组合层 + work_items 6 工具）之上，落地 **AI 调用 WorkNexus 的安全底座**：把 M3 散在每个工具里的 delegation 校验**上提为 `/mcp` 中间件**，对每个 MCP tool 调用做 **双 token 校验**（multirag server token + delegation token）+ **风险门禁**，并 **全量留痕**（`skill_invocations` 每次调用记一行）。对外暴露只读的 `GET /skills`（反射 MCP 组合层）与调用记录端点，前端提供 `/skills` 中心页。

这是 M5（AgentAction 确认流 / WorkChat）执行链路的**安全前置**：M5 才允许 AI 写库，M4 先把"谁在调、代表谁、什么风险、是否留痕"钉死。

验收（规格书 §4）：multirag 可调 `/mcp`；双 token 校验生效；能识别 represented_user；调用前后有 `skill_invocation`；权限不足被拒；**tool 参数无法伪造身份**。

### 本期范围（与用户敲定，方案 1：仅骨架 + 回填 workitem-skill）

- ✅ `/mcp` 双 token 中间件（server token + delegation）+ 统一 delegation 上下文（ContextVar）。
- ✅ `skill_invocations` 全量留痕表 + service。
- ✅ `GET /api/v1/skills`（反射）、`GET /api/v1/skills/invocations`、`GET /api/v1/skills/invocations/{id}`。
- ✅ 回填 `modules/work_items/mcp.py`：去掉 per-tool delegation 自校验，复用中间件上下文；6 工具补 `perm:` tag。
- ✅ 前端 `/skills` 只读中心页（Skill/Tool 列表 + 调用记录表 + 详情抽屉）。

### 写动作语义（本期关键约束，用户明确）

**M4 只有 `read` 工具真实执行**（`workitem_search_work_items` / `workitem_get_work_item` / `system_ping`）。

4 个 `low_write` 工具（create/update/transition/comment）在**中间件层被阻断**——仍登记、展示风险、记录一行
`skill_invocation`（`status=blocked`、`requires_confirmation=true`），但**绝不落库**，向调用方返回明确的
"requires AgentAction confirmation (M5)"。真正放开写执行等 M5 AgentAction 确认链路接上。`high_write` 一律拒绝
（v0.1 无此类工具）。

> 理由：D5 双重校验公式含"确认状态"，而 AgentAction 确认流属 M5。M4 在确认链路就绪前，不能让外部 AI 成为
> 可直接落库的通道。

### 明确不做 / 推迟

- **intake-skill** → 推迟 M6（intake 模块未建）。
- **knowledge-skill**（代理 multirag）→ 推迟 M5（multirag Adapter / D7 对接未建）。
- **project-skill / report-skill** 只读工具 → 不抢 M4 主线，最多作为 M4.1 余力项。
- 不建 `skills` / `skill_tools` 注册表：Skill/Tool 清单由 MCP 组合层**代码反射**得到（规格书 §10 允许）。
- AgentAction 确认流、自动执行策略、AI 上下文权限过滤（D6 的 multirag 侧）→ M5。
- AI 连接配置落库 / 设置页 → v0.1 以 `.env` 为准（D7）。

## 2. 数据模型

唯一新表 `skill_invocations`，用 `EntityMixin`（`id String(32)` / `tenant_id` / `created_at` / `updated_at`）。
枚举为 `schemas.py` 中 `StrEnum`，DB 存字符串；时间一律 UTC `TIMESTAMP(timezone=True)`。

| 模型 | 关键字段 | 说明 |
| --- | --- | --- |
| SkillInvocation（`skill_invocations`） | `skill_code String(50)`、`tool_name String(100)`（索引）、`caller_type String(20)`（`ActorType`）、`caller_id String(32)`（= MCP 调用方 agent_id）、`represented_user_id FK users`（索引，delegation 的 user_id）、`agent_id FK ai_agents`、`project_id FK projects?`、`conversation_id String(64)?`、`run_id String(64)?`、`input_summary Text`（脱敏截断）、`output_summary Text?`（脱敏截断）、`status String(20)`、`risk_level String(20)`、`requires_confirmation Boolean`、`agent_action_id String(32)?`（**M5 前恒为空**）、`audit_log_id FK audit_logs?`、`error_message Text?`、`started_at TIMESTAMP`、`finished_at TIMESTAMP?` | 每次 MCP tool 调用一行，成功/失败/阻断/拒绝**都记**。`represented_user_id` 来自 delegation token（非 tool 参数）。`agent_action_id` 为 M5 预留（暂不加 FK，agent_actions 表 M5 才建）。索引 `(tenant_id, created_at)` 便于列表倒序 |

### 枚举（schemas.py，StrEnum）

- `RiskLevel`: `read | low_write | high_write`（与 MCP tag、D4、M5 AgentAction 共用语义；本期定义于 skills，M5 可上提 core）
- `SkillInvocationStatus`: `running | success | failed | blocked | rejected`
  - `running`：写入起始行后、`call_next` 之前的在途态
  - `success` / `failed`：read 工具执行成功 / 抛错
  - `blocked`：low_write 在 M4 被阻断（待 M5 确认）
  - `rejected`：server/delegation 校验通过但风险或权限不允许（high_write、缺 effective 权限）
- `caller_type` 复用 `core.deps.ActorType`（`ai_agent`）

**脱敏策略**：`input_summary` 来自 tool `arguments`（截断到 ~2000 字符，敏感 key 名打码）；delegation token / server
token 在 headers，**不进** arguments，天然不入摘要。`output_summary` 取结果的紧凑摘要（如列表 `{items: n}`、详情
关键字段）截断。`error_message` 为异常消息截断脱敏。**任何字段绝不写入 token 明文**。

迁移：`uv run alembic revision --autogenerate -m "skills: skill_invocations"` 后人工审查（FK、索引、nullable）。

## 3. `/mcp` 双 token 中间件（核心）

`modules/skills/middleware.py` 定义 `SkillInvocationMiddleware(fastmcp Middleware)`，在 `worknexus/mcp.py` 经
`mcp.add_middleware(SkillInvocationMiddleware())` 注册在**根 server**，对所有请求（含 mounted 子 server 工具）生效。

### 双 token（D5 / D7）

- **Server token（请求来源）**：`Authorization: Bearer <WORKNEXUS_MCP_AUTH_TOKEN>`（`config.mcp_auth_token` 已存在）。
  multirag 在其 MCPServer.headers 配置该 Bearer。中间件用 `get_http_headers(include={"authorization"})` 读取
  （FastMCP 默认过滤 `authorization`，必须显式 `include`）。校验：缺/非 Bearer/不匹配 → 拒绝。**只证明来自 multirag**。
- **Delegation token（代表谁）**：`X-WorkNexus-Delegation: wn_del_xxx`（自定义 header，默认放行）。经 M1
  `verify_delegation_token` 还原 `DelegationContext(tenant/user/agent/project/conversation/run/permissions_snapshot)`。
- **tool 参数不得作为身份依据**；custom_header 禁止直传 user_id / email / session token。

### 风险门禁与执行判定（pure helper，测试主战场）

- `read_server_token(headers)` / `verify_server_token(token, settings)`
- `read_delegation_token(headers)`
- `risk_for_tool(name)`：反射 `mcp.get_tool(name).tags` 取 `read/low_write/high_write`（缓存；未知 tag → 拒绝）
- `permission_for_tool(name)`：反射工具的 `perm:<permission>` tag → 所需 `Permission`（无则仅需 `SKILL_INVOKE`）
- `decide_execution(risk, required_perm, snapshot) -> Decision`：
  - `high_write` → **reject**（`SKILL_RISK_FORBIDDEN`）
  - `required_perm ∉ snapshot["effective"]` → **reject**（`FORBIDDEN`）
  - `low_write` → **blocked**（M4，`SKILL_CONFIRMATION_REQUIRED`）
  - `read` → **allow**
- `summarize(value)`：截断 + 脱敏

**双重校验公式（M4 子集）**：用户权限 ∧ AI Agent 权限（= `permissions_snapshot.effective`，签发时已算
user∩agent∩project）∧ 资源权限（service 内 membership/archived 校验，M3 已具备）∧ 风险等级。**确认状态属 M5**
（low_write 在 M4 即落到 blocked）。WorkNexus 不信任 AI 平台的权限判断，落库前自行校验。

### `on_call_tool(context, call_next)` 流程

```text
1. headers = get_http_headers(include={"authorization"})
2. verify_server_token 失败 → ToolError(MCP_SERVER_TOKEN_INVALID)        # call_next 之前
3. delegation 缺失 → ToolError(MCP_DELEGATION_MISSING)
   开 log_db（独立 session）→ verify_delegation_token（无效/过期复用 4009/4010）→ Actor(AI_AGENT)
4. risk = risk_for_tool(name); perm = permission_for_tool(name)
   decision = decide_execution(risk, perm, ctx.permissions_snapshot)
5. log_db 写 skill_invocation(status=running, input_summary=summarize(arguments))
   + audit.record(SKILL_INVOKE, resource=skill_invocation, detail={tool,risk,decision}) → 回填 audit_log_id
6. reject / blocked（high_write、缺权限、low_write）：
   finalize(status=rejected|blocked, error_message) → log_db.commit() → raise ToolError   # 决不 call_next
7. allow（read）：
   另开 business_db；CTXVAR.set(MCPCallContext(business_db, actor, ctx))
   try: result = await call_next(context)
        finalize(success, output_summary=summarize(result))
   except: finalize(failed, error_message) → re-raise
   finally: CTXVAR.reset(...)
   log_db.commit(); return result
```

**两 session 设计**：`log_db`（取证留痕，成功/失败/阻断都必须持久化，即便业务事务回滚）与 `business_db`（read 执行）
分离 —— 满足"调用前后有 skill_invocation"且"Skill 调用失败必记"。FastMCP 中间件 `set_state` **不跨 mount 边界**，故
用我们自己的 `contextvars.ContextVar` 传递上下文，**不用** `ctx.set_state`。拒绝一律在 `call_next` 之前（FastMCP：
`call_next` 后 raise 只记日志不回客户端）。

### 回填 `modules/work_items/mcp.py`

- 删除 `_delegated()` 自读 header / 自校验；新增 `require_mcp_context()` 从 `CTXVAR` 取 `(db, actor, ctx)`
  （未设置 → `ToolError`，保留现有 in-memory 测试语义：无 header 调用仍被拒）。
- 6 工具补 `perm:<permission>` tag（如 `tags={"low_write", "perm:work_item.create"}`），供中间件与 `GET /skills` 反射。
- low_write 工具体在 M4 不可达（中间件先阻断），但仍读 CTXVAR 保持一致（防未来移除门禁时回退到双校验）。

## 4. 反射式 `GET /skills`

`service.list_skills(mcp)`：遍历 `await mcp.list_tools()`，按 namespace 前缀分组 → `skill_code`（`workitem` →
`workitem-skill`、`system` → `system-skill`）；每工具的 tags 解析 `risk` 与 `perm:`；`executable_in_v01 = risk == read`。
单一来源（反射），不建表。

## 5. REST API

错误码占 **6xxx** 段（`core/errors.py`）：

| 码 | 名 | 触发 |
| --- | --- | --- |
| 6001 | MCP_SERVER_TOKEN_INVALID | 缺 / 非 Bearer / 与 `mcp_auth_token` 不匹配 |
| 6002 | MCP_DELEGATION_MISSING | 缺 `X-WorkNexus-Delegation` header（无效/过期复用 4009/4010） |
| 6003 | SKILL_RISK_FORBIDDEN | high_write 工具被 AI 调用 |
| 6004 | SKILL_CONFIRMATION_REQUIRED | low_write 工具在 M4 被阻断（待 M5 AgentAction） |
| 6005 | SKILL_INVOCATION_NOT_FOUND | `GET /invocations/{id}` 不存在 / 跨 tenant |

> 权限不足复用通用 `FORBIDDEN=1004`。MCP 工具内的 `BizError` 经中间件转 `ToolError`（消息回传调用方）。

响应统一 `Envelope[...]`，schema 继承 `ApiModel`（camelCase）；列表用 `Page[SkillInvocationOut]`。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| POST | `/mcp`（streamable-http） | MCP 入口，双 token 中间件保护 | server token + delegation |
| GET | `/api/v1/skills` | 反射 MCP 组合层：Skill → Tool（风险 / 是否本期可执行） | `skill.read` |
| GET | `/api/v1/skills/invocations?status=&risk_level=&tool_name=&page=&page_size=` | 调用记录分页（tenant 作用域，倒序） | `skill.read` |
| GET | `/api/v1/skills/invocations/{id}` | 调用记录详情 | `skill.read` |

service 签名遵循 `async def list_invocations(db, actor, *, params, filters...)` / `get_invocation(db, actor, invocation_id)`。

### 输出 schema（ApiModel，camelCase）

- `SkillOut`：`skillCode`、`tools[] SkillToolOut`
- `SkillToolOut`：`toolName`、`riskLevel`、`executableInV01`、`requiredPermission?`
- `SkillInvocationOut`：全字段 + `representedUser?{id,displayName}`（join users 轻量嵌入）；`agentActionId` M5 前为 null

## 6. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/skills` | Skills 中心页（只读） | 上部 Skill/Tool 列表（反射，标 risk + 本期可执行/写需 M5 确认）；下部调用记录 DataTable（tool/skill/风险/状态/代表用户/是否需确认/AgentAction[M5 占位]/时间）+ risk/status 过滤 + 分页；行点击打开右侧 Sheet 详情（input/output 摘要、error、代表用户/agent/project/conversation/run）；三态 PageSkeleton/EmptyState/ErrorState |

i18n namespace：`skills`（zh-CN / en-US 同步提供，四步注册）。侧边栏入口 `PermissionGate permission="skill.read"`。
组件：`risk-badge`、`invocation-status-badge`（cva 变体，仅语义 token 类）、`skill-list`、`skill-invocation-columns`、
`skill-invocation-drawer`。借鉴 Plane 的 API token / activity feed 列表展示交互（仅 UI，安全模型遵循 D5/D6/§7）。

## 7. 审计与权限点

### 审计事件（`audit.service.AuditAction` 新增）

- `skill.invoke`：每次 MCP tool 调用一行（`detail` 含 tool / risk / decision / status），覆盖规格书 §8 的
  "MCP tool 调用" 与 "Skill 调用失败"。写在中间件 `log_db`（独立事务），与 `skill_invocation` 同提交、互相关联
  （`skill_invocation.audit_log_id`）。AI 动作可追溯链 `requested_by/agent_id/.../skill_invocation_id` 在 M5 补全
  （AgentAction 落地时）。

### 权限点（沿用 M1 矩阵，禁改）

- `skill.read`（全角色，含 viewer / ai_agent）：读 `GET /skills`、invocations。
- `skill.invoke`（仅 `ai_agent`）：MCP 调用的基线权限；具体工具另需其 `perm:` 对应权限 ∈ delegation `effective`。
- 校验唯一入口：REST 走 `require_permission(Permission.SKILL_READ)`；MCP 走中间件 `decide_execution`（基于
  `permissions_snapshot.effective`）。

## 8. 测试点

- **helper 单测**：server token（缺/非 Bearer/不匹配/匹配）、delegation 解析、`risk_for_tool`、`permission_for_tool`、
  `decide_execution`（read/low_write/high_write × 有/无 effective 权限矩阵）、`summarize` 脱敏（不含 token）。
- **middleware 单测**（`monkeypatch` `get_http_headers` + 手造 `MiddlewareContext` + fake `call_next`，真实 PG）：
  合法 read → `success` 落库；read 抛错 → `failed` 落库；low_write → `blocked` 落库且 `call_next` **未被调用**；
  缺/错 server token → `ToolError` 且不进 delegation；缺/错 delegation → `ToolError`。
- **service 单测**：`list_invocations` 分页/过滤、`get_invocation`（跨 tenant 404）、`list_skills` 反射
  （namespace→skill、tag→risk、executable_in_v01）。
- **in-memory `Client(mcp)`**：工具注册 + namespace + risk tag + `perm:` tag（保留 M3 用例，扩展断言）。
- **HTTP `/mcp` 冒烟**（`httpx.ASGITransport` + `StreamableHttpTransport(headers=...)`，fixture 经
  `issue_delegation_token` 发真实 token）：① 缺 server token → 被拒、无副作用；② 合法 server token + delegation 调
  `system_ping` / read 工具 → 跑通且 `skill_invocations` 多一行 `success`；③ low_write → 一行 `blocked` 且工作项未创建。
- **前端（vitest + msw）**：invocations 查询 hook、columns 渲染、风险/状态 Badge、详情抽屉。
- **E2E（轻量）**：登录 → `/skills` 列表渲染 + 详情抽屉打开（非核心闭环，最小覆盖）。

## 9. 参考实现对照（Plane，/Users/dxl/project/ts/plane，仅 UI 借鉴）

| 维度 | Plane | WorkNexus（本设计） | 理由 |
| --- | --- | --- | --- |
| 调用/活动留痕 | APIActivityLog（API token 调用日志） | skill_invocations（MCP tool 调用全量留痕 + 双 token 上下文） | M4 是 AI 安全架构，需记 represented_user / risk / 确认状态，Plane 无对应物 |
| 列表/详情交互 | API token、webhooks、integrations 列表 + 状态展示 | Skills 中心页 Skill/Tool 列表 + 调用记录表 + 详情抽屉 | 借鉴只读列表 + 状态 badge + 详情交互范式 |
| 鉴权模型 | API token（tenant 级） | 双 token（server token 来源 + delegation 身份穿透）+ 风险门禁 | D5/D6/§7 不可妥协，**不照搬** Plane 鉴权 |

**不照搬** Plane 的鉴权与数据建模；仅借鉴列表/活动 feed 的 UI 交互。Plane 仅参考，不做任何改动。

## 10. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-14 | （设计） | 初版设计：M4 仅骨架 + 回填 workitem-skill（project/report 余力、knowledge→M5、intake→M6 推迟）；skill_invocations 单表（represented_user/risk/status/audit_log 关联，agent_action M5 预留）；/mcp 双 token 中间件（Authorization Bearer server token + X-WorkNexus-Delegation，get_http_headers include authorization，reject-before-call_next，ContextVar 跨 mount 传上下文）+ 风险门禁（read 执行 / low_write 阻断待 M5 / high_write 拒）+ 全量留痕（log_db 独立事务，成功/失败/阻断都记）；回填 work_items/mcp.py（require_mcp_context + perm: tag）；反射式 GET /skills + invocations 端点；6xxx 错误码；AuditAction.skill.invoke；前端 /skills 只读中心页；测试以 helper/middleware 单测为主 + HTTP 冒烟；对照 Plane 仅 UI 借鉴 |
