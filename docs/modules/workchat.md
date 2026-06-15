# 模块：workchat（AI WorkChat + AgentAction + multirag Adapter）

> 状态：设计中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/workchat`
> 关联 module（后端）：`apps/server/src/worknexus/modules/workchat`

## 1. 目标与范围

M5 在 M1（身份/权限/delegation token）、M3（work_items service + 6 个 MCP 工具）、M4（`/mcp` 双 token 中间件 + `skill_invocations` 全量留痕 + 风险门禁）之上，落地 **"AI 真的能对话、提出写动作、人确认后才落库"的全链路**：

```text
用户在项目 AI Chat 发消息
  → WorkNexus 过 D6 权限过滤构建上下文 → 签发 delegation token
  → 调 multirag agent completions（SSE，custom_header 带 token）
  → multirag 推理；需要写时回调 WorkNexus /mcp 的 low_write 工具
  → 中间件不再阻断，而是创建 AgentAction(pending) + 回填 skill_invocation.agent_action_id + 回正常 tool result
  → WorkNexus 把 AI 文本流 + agent_action 事件透传给前端
  → 用户在 AgentActionCard 确认 → 实时双重校验 → dispatcher 调 work_items.service 落库
  → skill_invocation / audit_log 留痕 → 看板 / 仪表盘更新
```

边界（AGENTS §1）：WorkNexus 负责"数据 / 权限 / 确认 / 执行 / 审计"，本模块只做一个薄 **AI Adapter** 调已有 multirag 平台；**不在本项目内做 AI 编排**（模型、知识库、Agent/工具规划归 multirag）。

验收（规格书 §5）：真实调通 multirag 流式；proposed_action 不直接落库；high_write 被禁止执行；AgentAction 全链路可追溯 `requested_by / agent_id / approved_by / executed_at`；失败有错误记录；**AI 上下文只含当前用户可见数据**。

### 本期与用户敲定的关键设计抉择（A–H）

| 点 | 决策 |
| --- | --- |
| **A 提案来源** | **唯一主路径 = MCP 工具调用**。"proposed_action" 不是要求模型输出的文本协议，而是 AI 调 `low_write` WorkNexus 工具时，由中间件归一化产生的内部业务对象 `AgentAction(pending)`。**不解析 AI 文本里的 proposed_action**，不做 hybrid 双路径。（真实 multirag wire 只发 `text` / `tool_call` / `tool_result` 帧，无 `proposed_action` / `knowledge_result` 帧——见 §5。） |
| **B 执行** | 显式 **dispatcher** 把 `tool_name → work_items.service` 函数；**绝不重放 MCP HTTP、绝不直接调 tool body**。approve 时重跑**实时**双重校验（用户 ∧ Agent ∧ 资源 ∧ 风险 ∧ 确认）；`permissions_snapshot` 只作"提案时证据"，不替代实时权限。以 **AI Agent actor** 执行业务写入；`AgentAction` 记 `requested_by_user_id / approved_by_user_id / agent_id`。 |
| **C SSE 拓扑** | WorkNexus **代理转发**：浏览器 ↔ WorkNexus `/workchat/runs`（WorkNexus 自有干净事件 schema）↔ multirag（原始 envelope）。APIToken 与 delegation token **绝不进浏览器**。 |
| **D multirag 端点** | `AIClient` 抽象隔离 multirag；主线目标 = D7 `/api/v1/agents/{agent_id}/completions`；**实现真实 adapter 前必须 live-verify** 真实 path / body / header；`enhanced_chat_sse` 仅作可降级的兼容实现，**不作产品契约**。测试 / E2E 用 `FakeAIClient`。 |
| **E 数据模型** | `conversations / messages / agent_actions` 三表；`knowledge_refs`、`arguments`、`permissions_snapshot`、`result` 用 JSONB。 |
| **F 上下文过滤** | 上下文 = 当前项目元信息 + 本会话近段历史 + 显式引用且用户可读的工作项，逐项过 `can()`/`permissions_for` 后才出站；无跨项目数据；不预取知识（multirag 自行 RAG）。 |
| **G 前端** | `lib/sse.ts`（新建，AGENTS §5.1 唯一允许绕过 contracts client 的场景）；`AIChatPanel` + `AgentActionCard`（借鉴 Plane 活动 feed 信息密度，安全模型遵循 D5/D6/§7）。 |
| **H 错误码 / 审计 / 权限** | 新错误码段 **7xxx**；`AuditAction` 新增 proposed/approve/reject/execute；权限点复用既有 `WORKCHAT_USE`（聊天/runs）+ `AGENT_ACTION_CONFIRM`（确认/拒绝），底层写权限（`work_item.*`）approve 时实时校验。 |

### 明确不做 / 推迟

- **文本 proposed_action 解析** → 不作为 v0.1 生产写动作来源（决策 A）。
- **intake 类动作**（`create_intake_request` / `accept_intake_request`）→ 推迟 M6（intake 模块与其 MCP 工具未建）；dispatcher 留扩展位并在文档标注缺口。
- **knowledge_result 富卡** → 多 rag 当前未发现独立 knowledge 帧；v0.1 尽力而为：若 multirag 以 `tool_result`/`metadata` 带引用则透传 `knowledge` 事件，否则只渲染文本。
- **auto-execute 策略**（项目管理员配置部分 low_write 自动执行）→ 后置；v0.1 一律需确认。
- **AI 连接配置落库 / 设置页可写** → v0.1 以 `.env` 为准（D7）。
- **多 conversation / 会话管理 UI** → v0.1 每项目一个默认 conversation。

## 2. 数据模型（E）

`modules/workchat/models.py`，三表均用 `EntityMixin`（`id String(32)` / `tenant_id` / `created_at` / `updated_at`）；`agent_actions` 为重要业务表，另加 `created_by / updated_by`。枚举为 `schemas.py` 中 `StrEnum`，DB 存字符串；时间一律 UTC `TIMESTAMP(timezone=True)`。

| 模型 | 关键字段 | 说明 |
| --- | --- | --- |
| Conversation（`conversations`） | `project_id FK projects`（索引）、`title String(200)?`、`kind String(20)`（`default`，预留多会话）、`created_by String(32)?`、`deleted_at?` | 每项目一个默认 AI 会话；`get_or_create_default_conversation(db, actor, project_id)` 幂等获取。索引 `(tenant_id, project_id)` |
| Message（`messages`） | `conversation_id FK`（索引）、`role String(10)`（`MessageRole`）、`content Text`、`run_id String(64)?`、`agent_action_id FK agent_actions?`、`work_item_id FK work_items?`、`knowledge_refs JSONB?`、`created_by String(32)?`（user 消息为发起者，ai/system 为 null） | AI 文本流落定后写一行 `role=ai`；可关联一个 AgentAction 与一个 WorkItem。索引 `(conversation_id, created_at)` |
| AgentAction（`agent_actions`，+ `created_by/updated_by`） | `conversation_id FK?`、`message_id String(32)?`（plain ref，破 messages↔agent_actions 循环 FK）、`project_id FK projects`（索引）、`action_type String(64)`（`AgentActionType`，来自 tool_name 归一）、`arguments JSONB`（tool 调用参数）、`risk_level String(20)`（恒 `low_write`）、`status String(20)`（`AgentActionStatus`）、`requested_by_user_id FK users`（delegation 的 user）、`agent_id FK ai_agents`、`approved_by_user_id FK users?`、`approved_at?`、`rejected_at?`、`executed_at?`、`rejection_reason Text?`、`permissions_snapshot JSONB`（提案时证据）、`skill_invocation_id String(32)?`（plain ref，避免与 `skill_invocations.agent_action_id` 形成循环 FK）、`result_ref_type String(32)?`、`result_ref_id String(32)?`、`error_message Text?`、`expires_at TIMESTAMP?` | 一次 low_write 工具调用生成一行。`expires_at` 用于 pending 超时 → `expired`（读/approve 时惰性判定）。索引 `(tenant_id, status, created_at)`、`(project_id, status)` |

回填：`skill_invocations.agent_action_id`（M4 已是 nullable `String(32)`，**保持 plain 不加 FK**——与 `agent_actions.skill_invocation_id` 互为反向引用，加双 FK 会成环；提案时由中间件回填值）。

### 枚举（schemas.py，StrEnum）

- `MessageRole`: `user | ai | system`
- `AgentActionType`（v0.1 = 4 个 work_items low_write，规格书 §5 的 8 种中 intake 2 个推迟 M6、`search_work_items`/`get_project_summary` 是 read 不入 AgentAction）：`create_work_item | update_work_item | transition_work_item | comment_work_item`
- `AgentActionStatus`: `pending | approved | rejected | executed | failed | expired`（D4）
  - `pending`：中间件创建后待确认
  - `approved`：通过实时双重校验、执行前的瞬态（执行成功立即转 `executed`，可不持久暴露）
  - `executed` / `failed`：业务写入成功 / 抛错
  - `rejected`：用户拒绝
  - `expired`：超过 `expires_at` 未确认
- `RiskLevel` 复用 `skills.schemas.RiskLevel`（`read | low_write | high_write`）——本期暂不上提 core，import 复用以保单一语义。

**`action_type ← tool_name` 归一**：MCP 工具挂载 namespace `workitem`，工具名形如 `workitem_create_work_item`；归一去前缀得 `create_work_item`。`service._TOOL_TO_ACTION`（tool_name → AgentActionType）与 `_ACTION_PERMISSION`（AgentActionType → 底层 Permission）+ dispatcher 共用同一映射，未知工具拒绝。

迁移：`uv run alembic revision --autogenerate -m "workchat: conversations/messages/agent_actions"` 后人工审查（FK、索引、nullable），并在 `alembic/env.py` 与 `conftest.py` `import worknexus.modules.workchat.models`，否则 autogenerate/create_all 看不到表。

## 3. 模块边界与依赖方向（不引入循环 import）

AGENTS §4.1 把 AgentAction 归 **`workchat`** 模块。依赖单向：

- `skills.middleware` → `workchat.service.create_pending_agent_action(...)`（提案时）。
- `workchat.service` 执行 dispatcher → `work_items.service.*`（确认时）。
- `skills.service` 继续在中间件内独占 `skill_invocation` 生命周期（begin/finish/回填 `agent_action_id`），故 **`workchat` 不 import `skills`** → 无环。
- `decide_execution` 保持纯函数；仅其**返回值**变（新增 `defer` 动作），不纯的 `create_pending_agent_action` 调用落在中间件。
- `workchat.service` import：`work_items.service`、`identity.service`（取 agent 实时权限/`load_subject`）、`core.access`、`audit.service`、`config`、httpx（仅 ai_client）。**均不反向 import skills/workchat**。

## 4. 后端行为

### 4.1 提案（在 `/mcp` 中间件内，AI run 期间同步发生）

改 `modules/skills/middleware.py` 的纯函数 `decide_execution` 与中间件主体：

- `decide_execution(risk, perm, snapshot)`：`high_write`→reject；`perm ∉ snapshot.effective`→reject；**`low_write`+权限通过 → 新 `Decision(action="defer", status=..., ...)`**（替换 M4 的 `blocked`）；`read`→allow。
- 中间件遇 `defer`（此时已握有 tool 名 + arguments + `DelegationContext`）：
  1. `begin_invocation(...)` 已写 `skill_invocation(status=running)` + `skill.invoke` 审计（M4 既有）。
  2. 调 `workchat.service.create_pending_agent_action(log_db, delegation, tool_name=name, arguments=args, skill_invocation_id=inv.id, expires_at=...)` → 返回 `AgentAction`。该 service 内同事务写 `agent_actions` 行 + `ai.proposed_action.create` 审计。
  3. 回填 `inv.agent_action_id = action.id`；`finish_invocation(status=SUCCESS, output_summary="pending agent_action <id>")`。
  4. `log_db.commit()`，**返回正常 tool result**（非 ToolError）：`{"status": "pending_confirmation", "agentActionId": <id>, "requiresConfirmation": true}` —— 让模型自然回复"已生成待确认动作"。

> 与 M4 的差异点仅此一处：`low_write` 从 "blocked + ToolError" 改为 "defer + 创建 AgentAction + 正常返回"。`read` / `high_write` 行为不变。SkillInvocationStatus 复用 `SUCCESS`（语义："工具调用成功产生了一个待确认动作"），不新增状态以保持 M4 枚举稳定。

### 4.2 确认执行（REST，稍后由用户会话发起；delegation token 此时已过期，全部上下文从 AgentAction 行读取）

`workchat.service.approve_and_execute(db, actor: Actor(user), agent_action_id) -> AgentActionOut`：

1. 取 `agent_action`（tenant 作用域，404=`AGENT_ACTION_NOT_FOUND`）；惰性过期：超 `expires_at` 置 `expired` 并抛 `AGENT_ACTION_EXPIRED`；非 `pending` 抛 `AGENT_ACTION_NOT_PENDING`。
2. **实时双重校验**（D5 公式齐全）：
   - 用户权限：`can(user_subject, <底层 perm>, project)` **且** `can(user_subject, AGENT_ACTION_CONFIRM, project)`；
   - Agent 权限：实时 `load_subject(agent)` 后 `can(agent_subject, <底层 perm>, project)`（不信任 stale snapshot 授权）；
   - 资源权限：由 `work_items.service` 内的 membership/archived 校验承担（M3 既有 `ensure_project_writable`）；
   - 风险：`risk_level == low_write`（high_write 不会走到这里）；
   - 确认状态：此刻 = 用户已确认。
   底层 perm 由 `action_type` 映射（create→`work_item.create`，update→`work_item.update`，transition→`work_item.transition`，comment→`work_item.comment`）。
3. 构造 **AI Agent actor**（`ActorType.AI_AGENT`，id = `agent_action.agent_id`，tenant），经 dispatcher 执行：
   ```
   create_work_item     -> work_items.service.create_work_item(db, ai_actor, project_id, WorkItemCreateIn(**args),
                              source=WorkItemSource.AI_CHAT, source_ref_id=agent_action.id,
                              reporter_id=agent_action.requested_by_user_id)   # ← reporter_id 必传，否则 FK 踩坑
   update_work_item     -> work_items.service.update_work_item(db, ai_actor, work_item_id, WorkItemUpdateIn(**args))
   transition_work_item -> work_items.service.transition_work_item(db, ai_actor, work_item_id, WorkItemTransitionIn(**args))
   comment_work_item    -> work_items.service.create_comment(db, ai_actor, work_item_id, CommentCreateIn(**args))
   ```
4. 成功：`status=executed`、`executed_at`、`approved_by_user_id`、`approved_at`、`result_ref_type/id`（如新建工作项 id）；写 `agent_action.execute` 审计。失败：`status=failed` + `error_message`，审计记失败（仍记 approve）。
5. **`reporter_id` 陷阱**：`work_items.service.create_work_item` 默认 `reporter_id = actor.id`，而 `reporter_id` 是 `users` FK；AI actor 的 id 是 `ai_agents` 主键，不传 `reporter_id` 会 FK 违例。dispatcher 必须显式 `reporter_id=requested_by_user_id`。
6. **provenance**：`source=ai_chat`（用户视角："AI 在 WorkChat 建议并经人确认创建"），`source_ref_id=agent_action_id`；`skill_invocation` 已记录它经 MCP 工具产生（`source=mcp` 留给未来非 WorkChat 的外部 MCP 调用来源）。

`reject(db, actor, agent_action_id, reason?)`：guard pending；`status=rejected`、`rejection_reason`、`rejected_at`、`approved_by_user_id`（记录拒绝人）；写 `agent_action.reject` 审计。

### 4.3 REST API（`router.py`，统一 `Envelope[...]`，schema 继承 `ApiModel` camelCase，列表 `Page[T]`）

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/conversations` | 列项目会话（v0.1 仅默认会话，幂等创建） | `workchat.use` |
| GET | `/api/v1/conversations/{conversation_id}/messages?page=&page_size=` | 消息分页（倒序后翻正展示） | `workchat.use` |
| POST | `/api/v1/conversations/{conversation_id}/messages` | 落一条 `user` 消息（不触发 AI；触发 AI 走 runs） | `workchat.use` |
| POST | `/api/v1/workchat/runs` | **SSE 代理**：发起一个 AI 回合，流式回 WorkNexus 事件 | `workchat.use` |
| GET | `/api/v1/workchat/runs/{run_id}` | 回合状态（断流后查询补偿） | `workchat.use` |
| GET | `/api/v1/agent-actions?status=&project_id=&page=&page_size=` | 待确认/历史动作分页（tenant 作用域） | `workchat.use` |
| GET | `/api/v1/agent-actions/{id}` | 动作详情 | `workchat.use` |
| POST | `/api/v1/agent-actions/{id}/approve` | 确认 → 实时双重校验 → 执行 | `agent_action.confirm` |
| POST | `/api/v1/agent-actions/{id}/reject` | 拒绝（可带 reason） | `agent_action.confirm` |

service 签名遵循 `async def fn(db, actor, *, ...)`：`get_or_create_default_conversation`、`list_conversations`、`list_messages`、`create_user_message`、`list_agent_actions`、`get_agent_action`、`create_pending_agent_action`、`approve_and_execute`、`reject`、`start_run`（AI 编排，见 §5）。

### 4.4 错误码（H，占 7xxx 段，`core/errors.py`）

| 码 | 名 | 触发 |
| --- | --- | --- |
| 7001 | CONVERSATION_NOT_FOUND | 会话不存在 / 跨 tenant |
| 7002 | AGENT_ACTION_NOT_FOUND | 动作不存在 / 跨 tenant |
| 7003 | AGENT_ACTION_NOT_PENDING | approve/reject 一个非 pending 动作 |
| 7004 | AGENT_ACTION_EXPIRED | 动作已过 `expires_at` |
| 7005 | AI_PLATFORM_UNAVAILABLE | multirag 不可达 / 连接失败 |
| 7006 | AI_RUN_FAILED | multirag 回错误帧 / 流异常中断 |
| 7007 | WORKCHAT_RUN_NOT_FOUND | `GET /runs/{id}` 不存在 |

> 权限不足复用通用 `FORBIDDEN=1004`；底层工作项错误复用 2xxx（如 `INVALID_STATUS_TRANSITION=2002`、`PROJECT_ARCHIVED=2009`）由 dispatcher 透传到 `agent_action.error_message`。

## 5. AI Adapter（multirag SSE，决策 C/D/F）

`modules/workchat/ai_client.py`：

- `class AIClient(Protocol): async def stream_run(*, messages, context, delegation_token, agent_id) -> AsyncIterator[AIEvent]`。
- `FakeAIClient`：确定性帧序列（含一个 `tool_call` 帧驱动出 proposed action + text 帧 + done），用于单测 / E2E；经 settings/依赖注入选用（`WORKNEXUS_AI_CLIENT=fake|multirag`）。
- `MultiragAgentCompletionsClient`（真实）：httpx `AsyncClient` 流式；`Authorization: Bearer <ai_platform_api_key>`；delegation token 放 custom_header；**TODO：实现前 live-verify** 真实 endpoint / body 字段 / custom_header 名 / SSE envelope（见 §11 开放项）。若 agent completions 不可用，落 `MultiragEnhancedChatClient` 兼容实现并在变更记录注明。
- `parse_sse_frame(line: str) -> AIEvent | None`：**纯函数**，用从 ts/web 反推的 envelope 夹具单测。

### multirag wire（从 ts/web 反推，§5 三类 ≠ wire 帧）

SSE 每行 `data: {JSON}\n\n`；envelope `{ retcode, retmsg?, data, start_to_think?, end_to_think? }`，`data` 为：
- `true` → 流结束（complete）
- `string` → 文本（旧式累积/增量）
- `{ type, content }`：`type ∈ text | tool_call | tool_result | tool_start | tool_end | error | metadata`
  - `text` → `content` 文本（增量或累积，解析端去重/合并）
  - `tool_call` → `content {tool_name, arguments, call_id}`（AI 决定调 WorkNexus 工具）
  - `tool_result` → `content {tool_name, call_id, result?, success, error?}`（其中我们 low_write 工具的 result 即 `pending_confirmation` 体）
  - `error` → 错误；`metadata` → token 计数等

**关键**：multirag **不发** `proposed_action` / `knowledge_result` 帧。proposed action 由 §4.1 的 /mcp 再入调用在服务端落库；`message` ← text 帧合并；`knowledge` ← 若有 `tool_result`/`metadata` 带引用则尽力透传。

### 回合编排 `start_run(db, actor, *, conversation_id, user_message)`（D6）

0. **选 agent（internal/external 分离，铁律）**：`resolve_agent(db, actor, settings) -> ResolvedAgent{internal_agent_id, external_agent_id}`。`WORKNEXUS_AI_PLATFORM_DEFAULT_AGENT_ID` 是 multirag 的**外部** agent id（setup 写入 `ai_agents.external_agent_id`）。选优先级：external id 命中的 active agent → 首个有 external id 的 active agent → 首个 active agent。**WorkNexus 不做 AI 编排，但必须做 AI 身份治理**：`internal_agent_id`（= `ai_agents.id`）是本地安全/权限/审计主体；`external_agent_id`（= `ai_agents.external_agent_id`）才是 multirag 真实执行入口。无 external id 时：multirag 模式抛 `AI_PLATFORM_UNAVAILABLE`；`fake` 模式回退到 internal id（fake 忽略它，不影响测试/E2E）。
1. 落 `user` 消息。
2. **构建上下文并权限过滤**：当前项目元信息（`can(project.read)`）+ 本会话近 N 条历史 + 显式引用且 `can(work_item.read)` 的工作项；逐项过滤后才组 `messages/context`。**用户看不到的，不进 prompt。**
3. `issue_delegation_token(db, actor, user_id=actor.id, agent_id=`**`internal_agent_id`**`, project_id, conversation_id, run_id)` —— delegation 绑**内部** agent id（multirag 回调 `/mcp` 时只认它做权限/审计）。
4. `ai_client.stream_run(..., agent_id=`**`external_agent_id`**`)` —— 真实 client 用它拼 `/api/v1/agents/{external}/completions`；对每帧 `parse_sse_frame`：text → 累积 + 发 `message_delta`；tool_call/tool_result → 服务端已落 AgentAction，查/带出 `AgentActionOut` 发 `agent_action` 事件；metadata/knowledge → `knowledge`；error → `error`。
5. 流终：落 `ai` 消息（关联首个 agent_action / work_item），发 `message_done` + `done`。

### WorkNexus → 前端 SSE 事件 schema（干净、后端封装，原始 multirag 格式不外泄）

`message_delta {content}` | `message_done {messageId}` | `agent_action {action: AgentActionOut}` | `knowledge {references}` | `error {code, message}` | `done`。

## 6. UI / 页面（G）

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/projects/{id}/ai` | 项目 AI Chat | 消息列表（user/ai 气泡，AI 文本经 `lib/markdown.tsx` sanitize 渲染）+ 输入框 + SSE 流式增量；行内 `AgentActionCard`（动作类型 + 参数/diff 展示 + 确认/拒绝，确认经 `ConfirmDialog`）；`KnowledgeReferenceCard`（知识引用）；三态 `PageSkeleton/EmptyState/ErrorState`；入口 `PermissionGate permission="workchat.use"` |

- `lib/sse.ts`（**新建**，AGENTS §5.1 唯一允许绕过 contracts client 的封装）：`streamRun(url, body, { signal, onEvent })` —— POST + `credentials:'include'`（会话在 HttpOnly cookie），读 `ReadableStream`，按 `data:` 分帧 `JSON.parse`，分发 WorkNexus 事件 schema。**不用 `EventSource`**（需 POST + cookie）。
- `features/workchat/api/`：Key Factory（`workchatKeys` / `agentActionKeys`）；`useConversationsQuery` / `useMessagesQuery` / `useAgentActionsQuery` / `useAgentActionQuery`；`useApproveAgentActionMutation` / `useRejectAgentActionMutation`（`meta.suppressToast`，成功 invalidate messages + agent-actions）；`useWorkchatRun`（包 `lib/sse.ts`，流式态 + 终态 invalidate）。
- 组件：`AIChatPanel`、`MessageBubble`（AI 文本经 `<Markdown>`）、`AgentActionCard`、`KnowledgeReferenceCard`、`agent-action-status-badge`（cva 变体，仅语义 token 类）。
- `paths.ai(projectId)` = `/projects/${projectId}/ai`；router 懒加载于 `AppShell`/`RequireAuth` 下。
- i18n namespace：`workchat`（zh-CN / en-US 同步，四步注册：`locales/index.ts` + `i18n.ts` `ns`+`AppTFunction` + `i18next.d.ts`）。
- **手册补条**（AGENTS §5.5，新场景先补手册再写业务）：① SSE 流式（统一封装于 `lib/sse.ts`，签名如上）；② AgentActionCard（确认动作的统一卡片：参数/diff 展示 + approve/reject + ConfirmDialog）。

## 7. 审计与权限点

### 审计事件（`audit.service.AuditAction` 新增，覆盖规格书 §8）

- `ai.proposed_action.create`：中间件创建 AgentAction(pending) 时（detail 含 action_type / risk / skill_invocation_id）。
- `agent_action.approve` / `agent_action.reject` / `agent_action.execute`：approve/reject/执行成功或失败时（execute 的 detail 含 result_ref / error）。
- AI 动作可追溯链：`requested_by_user_id`（AgentAction）+ `agent_id` + `approved_by_user_id` + `skill_invocation_id` + `executed_at`（规格书 §8 要求）。审计写在 service 层与业务同事务。

### 权限点（沿用 M1 矩阵，禁改）

- `workchat.use`：聊天、读会话/消息、发消息、发起 run、读 agent-actions（全成员角色具备）。
- `agent_action.confirm`：approve / reject（项目管理员 / 具备者；**AI_AGENT 无此权限**，确认只能人做）。
- 底层写权限（`work_item.create/update/transition/comment`）：approve 时对**用户与 Agent 实时**校验。
- 校验唯一入口：REST 走 `require_permission`；MCP 提案走中间件 `decide_execution`（基于 `permissions_snapshot.effective`）；执行走 `approve_and_execute` 内的实时 `can()`。

## 8. 测试点

- **decide_execution 单测**（扩展 M4 矩阵）：`low_write`+权限通过 → 新 `defer`（不再 blocked）；`high_write`→reject；缺 effective 权限→reject；`read`→allow。
- **middleware 单测**（真实 PG）：`low_write` defer → 创建 `agent_actions` 一行 + 回填 `skill_invocation.agent_action_id` + 返回 `pending_confirmation` 正常 result（**非 ToolError**）；`high_write` 仍拒。
- **service 单测**：`create_pending_agent_action`（字段/快照/审计）；`approve_and_execute` 成功（落工作项，`source=ai_chat`、`source_ref_id`、`reporter_id`=user）、失败（业务异常→`failed`+error）、实时校验拒绝（用户/Agent 缺权限→FORBIDDEN）、过期（`expired`）、非 pending（`AGENT_ACTION_NOT_PENDING`）；`reject`；`get_or_create_default_conversation` 幂等。
- **SSE 解析纯函数单测**：用反推 envelope 夹具喂 `parse_sse_frame`（text 合并/去重、tool_call/tool_result、error、metadata、`data:true` 终止、旧式 string、think 标记）。
- **AIClient 编排单测**：`FakeAIClient` 驱动 `start_run` → 落 user/ai 消息 + 产出 AgentAction + 发 WorkNexus 事件序列；D6 上下文过滤（不可见工作项不进 context）。
- **in-memory `Client(mcp)`**：low_write 工具调用经中间件 → 产出 pending AgentAction（替换 M4 "断言被阻断" 用例）。
- **HTTP 冒烟**（`httpx.ASGITransport`）：`/workchat/runs`（FakeAIClient）流式跑通；`/agent-actions/{id}/approve` 落库 + 看板可见；双 token 回环（`issue_delegation_token` 发真实 token → `/mcp` low_write → AgentAction）。
- **前端（vitest + msw）**：`lib/sse.ts` 解析、query/mutation hooks、`AgentActionCard` 确认/拒绝交互、状态 Badge。
- **E2E（Playwright，主链路，`FakeAIClient`）**：登录 → 项目 AI Chat 发消息 → AI 流式 → `tool_call`→`AgentAction(pending)` → `AgentActionCard` → 确认 → 工作项落库（`source=ai_chat`）→ 看板 + 仪表盘反映；+ 语言/主题切换。**真实 multirag 流式手动验证**（endpoint/body live-confirm 后）。
- 覆盖率门槛：后端 service ≥85% / 整体 ≥70%；前端 `lib/` + stores ≥80%。

## 9. 参考实现对照（仅交互借鉴，安全/建模遵循 D4–D7 / §7）

| 维度 | 参考源 | WorkNexus（本设计） | 理由 |
| --- | --- | --- | --- |
| AI 对话 / SSE 流式 / 工具调用时间线 | ts/web（疑似 multirag 前端，`/Users/dxl/project/ts/web`，只读） | `lib/sse.ts` + `AIChatPanel`，但解析 WorkNexus 自有事件 schema（非原始 envelope）；落 WorkNexus 写法 | 反推 **wire format** 与 tool_call 帧；交互范式借鉴，不照搬其 api client / Tailwind3 |
| 评论/活动 feed、确认项呈现 | Plane（`/Users/dxl/project/ts/plane`，只读） | `AgentActionCard` 信息密度 + agent-actions 待确认列表 | OSS Plane **无** AI WorkChat/AgentAction 对应物；仅借鉴 UI 密度，安全模型为 WorkNexus 独有 |
| AI 安全模型（双 token / delegation / 确认链路） | —（无对应物） | D5/D6/§7 全套 | 不可妥协，不照搬任何参考源 |

## 10. PR 拆分（一 PR 一意图；squash merge）

1. **本设计文档**（workchat.md）+ 同步 roadmap M5 进度。（当前 PR）
2. **后端核心**：模型 + Alembic 迁移（`alembic check` 干净）+ `workchat.service`（create_pending / approve_and_execute dispatcher / reject / list/get / conversations+messages）+ REST（不含 AI 出站）+ 改 `skills` `decide_execution`/中间件 `low_write`→`defer` + 7xxx 错误码 + AuditAction。测试：service 单测、双 token→AgentAction（in-memory `Client`）、HTTP 冒烟。
3. **AI Adapter**：`AIClient` 协议 + `FakeAIClient` + `MultiragAgentCompletionsClient`（live-verify）+ `parse_sse_frame` 纯函数 + `/workchat/runs` 流式。测试：SSE 解析夹具、`FakeAIClient` 编排、上下文过滤。
4. **contracts**：`npm run contracts:generate`（生成产物单独 commit）。
5. **前端**：`lib/sse.ts` + workchat feature（hooks / AIChatPanel / AgentActionCard / …）+ i18n + router + paths.ai + 手册条目（SSE / AgentActionCard）。vitest（sse 解析 / hooks via msw / 卡片）+ Playwright E2E 主链路（`FakeAIClient`）。

## 11. 开放项（PR3 内解决，不阻塞设计）

Live-verify 真实 multirag 端点：`POST /api/v1/agents/{agent_id}/completions` 是否存在、确切 body 字段、custom_header 如何传 delegation、SSE envelope 是否即从 ts/web 反推的 `{retcode, data:{type,content}}` 形态。若仅 `enhanced_chat_sse` 可用，落 `MultiragEnhancedChatClient` 作**有文档的兼容实现**，**不改业务设计**（仍以 D7 agent/workflow completions 为产品主契约）。

## 12. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-15 | M6 接入（dispatcher 扩展） | 填补 §"明确不做 / 推迟" 标注的 intake dispatcher 缺口：`AgentActionType` 新增 `create_intake_request` / `accept_intake_request`；`_TOOL_TO_ACTION` / `_ACTION_PERMISSION` 加 intake 两映射（→`intake.create` / `intake.triage`）；`_dispatch` 拆为 `_dispatch_work_item_action` / `_dispatch_intake_action`（直接扩展，未引入 handler registry——6 个动作不值得抽象）；新增单向依赖 `workchat.service → intake.service`（intake 不反向依赖 workchat，无环）。详见 docs/modules/intake.md PR3 |
| 2026-06-15 | fix（agent id 分离） | 修正 internal/external agent id 混用（接真实 multirag 的前置）：`resolve_agent_id(->str)` 改 `resolve_agent(->ResolvedAgent{internal_agent_id, external_agent_id})`；`start_run` 改收 `agent: ResolvedAgent`，`issue_delegation_token` 用 **internal**（`ai_agents.id`，权限/审计主体）、`ai_client.stream_run` 用 **external**（`ai_agents.external_agent_id`，multirag completions URL），ProposeAction 的 DelegationContext 同用 internal；`WORKNEXUS_AI_PLATFORM_DEFAULT_AGENT_ID` 明确为 multirag 外部 id；multirag 模式无 external id 抛 `AI_PLATFORM_UNAVAILABLE`、fake 模式回退 internal；`.env.example` 补 `WORKNEXUS_AI_CLIENT`/`_DEFAULT_AGENT_ID`/`_TIMEOUT_SECONDS`；§5 文档写明身份治理铁律；测试替换为 5 项（external 命中/回退/multirag 无 external 抛错/fake 回退/start_run 用 internal 签 delegation·external 调 client），全套 171 passed，ruff/mypy 全绿 |
| 2026-06-15 | PR5（前端 + E2E） | `lib/sse.ts` `streamSSE`（fetch + ReadableStream + credentials，按 `data:` 分帧，畸形帧跳过）；`features/workchat`：Key Factory + `useConversationsQuery`/`useMessagesQuery`/`useAgentActionsQuery` + `useApprove/RejectAgentActionMutation`（invalidate agentActions）+ `useWorkchatRun`（包 sse，累积 draft/liveActions、终态 invalidate messages+agentActions）；组件 `AIChatPanel`（消息流 + 输入 + pending 动作卡片 union 去重 + 三态）、`MessageBubble`（AI 文本经 lib/markdown sanitize）、`AgentActionCard`（动作类型/参数/状态 Badge + 批准/拒绝直调 mutation，卡片即确认面）、`KnowledgeReferenceCard`、`AgentActionStatusBadge`；`routes/ai-page.tsx` at `paths.ai`（router 懒加载 + project-detail 入口按钮 gated workchat.use）；i18n `workchat` namespace 四步注册 zh/en + projects.detail.aiChat；api-client 导出 `API_BASE_URL`；后端加 fake-only `ProposeAction` 事件 + 默认脚本（E2E 驱动全链路，真实路径仍走 /mcp 网关）+ `skill_invocation_id` 可空；§5.5 手册新增「AI 流式 SSE」「AI 动作确认卡片」并同步 AGENTS↔CLAUDE；vitest +4（sse 解析 3 + agentActions hook 1）；Playwright E2E `workchat.spec`（发消息→流式→proposed_action 卡片→批准→工作项落库）1 passed；web lint(0 err)/typecheck/test(26)/build 全绿；后端 167 passed |
| 2026-06-15 | PR3（AI Adapter + runs） | `ai_client.py`：`AIEvent`（TextDelta/ToolCall/ToolResultEvent/KnowledgeEvent/ErrorEvent/DoneEvent）+ `AIClient` Protocol（非 async 签名匹配 async generator）+ **`parse_sse_frame` 纯函数**（从 ts/web 反推的 `{retcode,data}` envelope → text/tool_call/tool_result/error/metadata，容错跳过噪声帧）+ `FakeAIClient`（脚本回放，tests/E2E/离线）+ `MultiragAgentCompletionsClient`（httpx 流式打 D7 `/api/v1/agents/{id}/completions`，**标注实现前须 live-verify** path/body/header §11）+ `get_ai_client(settings)` 按 `WORKNEXUS_AI_CLIENT=fake|multirag` 选型；`runs.py`：`build_context`（D6 权限过滤：project 过 `can(project.read)`、引用工作项过 `can(work_item.read)`、会话历史；均过滤后才出站）+ `resolve_agent_id`（默认 agent 缺省回退租户首个 active agent）+ `start_run`（落 user 消息 → 建上下文 → `issue_delegation_token`(绑定 conversation+run) → 流式消费 AIEvent → 仅**透出**已由中间件落库的 AgentAction〔从 tool_result 的 agentActionId 反查，绝不从流创建〕 → 落 ai 消息〔run_id+首个 agent_action_id〕 → 发 WorkNexus 事件 message_delta/agent_action/knowledge/error/message_done/done，异常一律转 error 不中断流）；service 加 `create_ai_message`/`get_run`（断流补偿，作用域校验）、`_get_conversation`→公开 `get_conversation`；schema `RunCreateIn`；router `POST /workchat/runs`（StreamingResponse text/event-stream，流前校验会话+权限避免半开响应）+ `GET /workchat/runs/{run_id}`；config `ai_client`/`ai_platform_timeout_seconds`；httpx 提为运行时依赖；测试 +23（parse_sse_frame 夹具 12、FakeAIClient、start_run 编排 6〔文本/agent_action 透出/error/D6 含与排除/resolve_agent_id〕、HTTP SSE 冒烟 monkeypatch fake）；全套 166 passed，ruff/mypy 全绿 |
| 2026-06-15 | PR2（后端核心） | `conversations/messages/agent_actions` 模型 + 迁移 `23b3888b116f`（alembic up/down/check 干净，env.py+conftest.py 注册 workchat.models；message_id/skill_invocation_id 用 plain ref 破循环 FK）；schemas（MessageRole/AgentActionType/AgentActionStatus StrEnum + Conversation/Message/AgentActionOut + MessageCreateIn/AgentActionRejectIn）；service（get_or_create_default_conversation 幂等、list/create messages、create_pending_agent_action〔中间件提案入口，写 ai.proposed_action.create 审计〕、approve_and_execute〔三段式 commit：approve→dispatch→executed/failed，实时双重校验 user∧agent∧resource∧risk∧确认，`_TOOL_TO_ACTION`/`_ACTION_PERMISSION`/`_dispatch` 显式映射到 work_items.service，以 AI Agent actor 执行且 `reporter_id=requested_by_user_id`、`source=ai_chat`、`source_ref_id=agent_action_id`〕、reject、list/get_agent_actions 按 accessible_project_ids 作用域）；deps（require_conversation_permission/require_agent_action_permission 解析 project 作项目级校验 + accessible_project_ids）；router（conversations/messages + agent-actions list/get/approve/reject，operation_id 供 orval，**不含 AI 出站 /workchat/runs〔PR3〕**）；改 skills `decide_execution` low_write `blocked`→`defer`、中间件 defer 分支创建 AgentAction(pending)+回填 skill_invocation.agent_action_id+返回正常 `pending_confirmation` ToolResult（非 ToolError）；errors 7001–7007；AuditAction ai.proposed_action.create/agent_action.approve/reject/execute；config `agent_action_pending_ttl_seconds`；api 注册 workchat_router；测试 12 项（service 9：幂等/提案+审计/执行+provenance/非 pending/过期/无权限/失败 dispatch/拒绝/list 作用域，REST 3：会话+消息/approve 落库/reject）+ 改 M4 helper/middleware 用例为 defer 语义；全套 143 passed，ruff/mypy 全绿 |
| 2026-06-14 | PR1（设计） | 初版设计：与用户敲定 A–H（A 提案唯一走 MCP 工具调用、中间件 `low_write` 由 blocked 改 `defer` 创建 AgentAction(pending)；B 显式 dispatcher→work_items.service、以 AI Agent actor 执行且必传 `reporter_id=requested_by_user_id`、approve 时实时双重校验、snapshot 仅作证据；C WorkNexus 代理 SSE，token 不进浏览器；D AIClient 抽象主线 D7 agent completions、实现前 live-verify、enhanced_chat_sse 仅兼容；E conversations/messages/agent_actions 三表 + JSONB；F 项目+会话历史+引用工作项的权限过滤上下文；G lib/sse.ts + AIChatPanel/AgentActionCard；H 7xxx 错误码 + AuditAction proposed/approve/reject/execute + 复用 workchat.use/agent_action.confirm 权限）；模块边界单向依赖（skills→workchat.create_pending、workchat→work_items，无环）；multirag wire 从 ts/web 反推（text/tool_call/tool_result，无 proposed_action/knowledge_result 帧）；5 个 PR 拆分；intake 动作推迟 M6；同步 roadmap M5 进度 |
