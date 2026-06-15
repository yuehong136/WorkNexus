# 模块：intake（请求池 / 分诊 / 转工作项）

> 状态：设计中
> 负责人：dxl
> 关联 feature（前端）：`apps/web/src/features/intake`
> 关联 module（后端）：`apps/server/src/worknexus/modules/intake`

## 1. 目标与范围

M6 把"四面八方进来的需求 / 反馈 / 工单线索"收进一个**项目级请求池**，由人（在**建议性** AI 分诊辅助下）逐条分诊：接受（转成工作项）、拒绝、标记重复、稍后处理。建立在 M2（projects）、M3（work_items service + 看板）、M4（`/mcp` 双 token 中间件 + skill_invocations）、M5（WorkChat + AgentAction 确认链）之上。

```text
请求进入（manual 表单 / ai_chat 经 AgentAction / 预留 api·mcp）
  → 落 intake_requests(status=new) + 规则引擎同步产出 advisory 建议（摘要/分类/类型/优先级，带 provenance）
  → 人在 /projects/{id}/intake 分诊
      accept  → 同一事务创建 WorkItem(source=intake, source_ref_id=intake.id) + 回填 converted_work_item_id → status=converted
      reject  → status=rejected（+ 原因）
      mark-duplicate → status=duplicate（+ duplicate_work_item_id）
      snooze  → status=snoozed（+ snooze_until；到期惰性回 new）
  → 审计全程留痕（intake.create/update/accept/reject/duplicate/snooze + work_item.create）
```

边界（AGENTS §1）：WorkNexus 负责"数据 / 权限 / 确认 / 执行 / 审计"。AI 只产出**建议**（不自动落库）；AI 发起的 `create_intake_request` / `accept_intake_request` 写动作必须经 M5 既有 low_write → AgentAction 确认链。

### 本期与用户敲定的关键设计抉择（A–H）

| 点 | 决策 |
| --- | --- |
| **A 分诊生成** | **规则版 `TriageEngine`（可替换 Provider）**。`RuleBasedTriageEngine`（v0.1）+ 未来 `MultiragTriageEngine`。建议**仅作展示与转换表单预填，绝不自动采纳**。不依赖 M5 仍待 live-verify 的 multirag 端点，使 intake 创建保持确定性、E2E 稳定（D7 明确允许"先规则后 multirag"）。建议带 **provenance**（`provider/version/reason/generatedAt/confidence?`）以便后续切 multirag 时审计可分辨来源。`suggested_assignee_id` 服务端校验为当前项目成员，无唯一匹配→`null`（规则不"猜人"）。 |
| **B 来源范围** | `manual`（真实 REST 表单）与 `ai_chat`（真实，经 AgentAction dispatch）**真接**；`mcp` 与 work_items 同样**预留**：`create_intake_request` 是 low_write，恒走 defer 建 AgentAction，tool body 不直接执行，故 WorkChat 内经 MCP 产生的 intake 实为 `source=ai_chat`，`mcp` 值留给未来非 WorkChat 外部 MCP 来源；`api` 与 email/IM 仅枚举/字段**占位**（真实外部渠道 roadmap 推迟 v0.4）。 |
| **C 接受语义** | **单步 accept = 接受并转换，原子**。`POST /intake/{id}/accept` 在**同一事务**内创建 WorkItem + 回填 `converted_work_item_id` + `status→converted`。`accepted` 为**保留**枚举值，v0.1 不由任何 endpoint 产出。需对 `work_items.service.create_work_item` 做小重构（其当前内部 commit）。 |
| **D dispatcher** | **直接扩展 M5 dispatcher（不做 handler registry）**。intake 两个 tool→action 映射 + 权限加入 workchat 既有字典；`_dispatch` import 并调 `intake.service`。`workchat` 可依赖 `intake`，`intake` **绝不**依赖 `workchat`（保持无环）。`_dispatch` 拆为 `_dispatch_work_item_action` / `_dispatch_intake_action` 仅为可读性。6 个动作不值得引入注册表。 |
| **E 来源关系** | **用 source/ref id 表达，不建 relation 行**。`work_item.source=intake` + `source_ref_id=intake.id` + `intake.converted_work_item_id` + 审计。**不建** `WorkItemRelation(created_from_intake)`——其两端 FK 都指向 `work_items.id`，结构上无法指向 intake（与 M5 用 source 字段表达 `created_from_message`、从不建 relation 行一致）。`RelationType.CREATED_FROM_INTAKE` 保持 M3 **保留枚举**。 |
| **F 前端** | DataTable 收件箱 + 状态/来源筛选 + 右侧 **Sheet** 详情抽屉（§5.5：详情查看→Sheet）。抽屉内分诊动作；accept 开小型转换 **Dialog**（用建议预填）；reject→`ConfirmDialog`（+ 可选原因）；mark-duplicate→工作项选择器 Dialog；snooze→日期选择器 Dialog。 |
| **G 错误码/审计/权限** | 错误码占 **3xxx** 段；`AuditAction` 新增 intake.create/update/accept/reject/duplicate/snooze；**复用既有三个权限**（`intake.read/create/triage`，不改 access.py→不触发 contracts 连锁；spec 的 accept/reject 收敛进 triage）。 |
| **H M7/M8 衔接** | M6 只保证 intake 数据可查、provenance/审计可追溯。Intake 转化率统计归 **M7 dashboards**、Home"待处理 intake"归 **M8**；M6 不出 dashboard 卡片/home 组件。 |

### 明确不做 / 推迟

- **multirag 实时分诊** → 后续 provider（M5 端点 live-verify 后）；v0.1 仅规则版。
- **真实 api/webhook/email/IM 入口** → roadmap v0.4（仅预留枚举/字段）。
- **AI 发起 reject/mark-duplicate/snooze** → v0.1 仅人工（AI 只暴露 create/accept 两个 low_write 动作；限制 AI 写面）。
- **删除 intake**（软删 `deleted_at` 预留但无 endpoint）、**两步 accepted→converted**、**到期自动重算建议**（终态行不重算）。

## 2. 数据模型

`modules/intake/models.py`，`IntakeRequest`（表 `intake_requests`）用 `EntityMixin`（`id String(32)` / `tenant_id` / `created_at` / `updated_at`）+ 重要业务表追加 `created_by / updated_by` + `deleted_at`（软删预留，v0.1 无删除 endpoint）。枚举为 `schemas.py` 中 `StrEnum`，DB 存字符串；时间一律 UTC `TIMESTAMP(timezone=True)`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `project_id` | FK `projects.id` ondelete CASCADE（索引） | intake 项目级 |
| `title` | `String(300)` | |
| `description` | `Text?` | |
| `source` | `String(20)` default `manual` | `IntakeSource` |
| `source_ref_id` | `String(64)?` | ai_chat 来源记 agent_action.id |
| `status` | `String(20)` default `new` | `IntakeStatus` |
| `submitter_id` | FK `users.id` nullable | users FK（同 `work_items.reporter_id`）；AI/系统来源→发起用户或 null。**不做多态 id** |
| `ai_summary` | `Text?` | 规则输出 |
| `ai_category` | `String(40)?` | 规则输出 |
| `suggested_type` | `String(20)?` | `WorkItemType` 值 |
| `suggested_priority` | `String(10)?` | `WorkItemPriority` 值 |
| `suggested_assignee_id` | FK `users.id` nullable | 服务端校验为项目成员 |
| `triage_meta` | `JSONB?` | 建议 provenance：`provider/version/reason/generatedAt/confidence?` |
| `duplicate_work_item_id` | FK `work_items.id` nullable | mark-duplicate 写入 |
| `converted_work_item_id` | FK `work_items.id` nullable | accept 写入 |
| `snooze_until` | `TIMESTAMP(tz)?` | snooze 写入 |
| `rejection_reason` | `Text?` | reject 写入 |

约束/索引：`Index("ix_intake_requests_project_status", "project_id", "status")`；`tenant_id` 由 EntityMixin 索引；**`UniqueConstraint("converted_work_item_id")`**（DB 级防重复 accept 产出双工作项；Postgres 允许多 NULL，仅对已设值唯一）。

枚举（`schemas.py`，StrEnum）：

- `IntakeSource`: `manual | ai_chat | api | mcp`（email/IM v0.4+，不入 v0.1 枚举）
- `IntakeStatus`: `new | triaging | accepted | rejected | duplicate | snoozed | converted`

> **来源关系澄清**（E）：`RelationType.CREATED_FROM_INTAKE` 是 M3 起就存在的保留枚举值，M6 **不**写 `work_item_relations` 行——`IntakeRequest` 不是 `WorkItem`，无法满足该表两端 `work_items.id` FK。v0.1 来源链 = `WorkItem.source/source_ref_id` + `IntakeRequest.converted_work_item_id` + 审计。

迁移：`uv run --directory apps/server alembic revision --autogenerate -m "intake: intake_requests"`，人工审查 FK/索引/nullable，并在 `alembic/env.py` 与 `conftest.py` `import worknexus.modules.intake.models`，`alembic check` 干净。

### 状态机（v0.1）

```text
new / triaging / snoozed  --accept-->         converted   （同一事务创建 WorkItem）
                          --reject-->          rejected
                          --mark-duplicate-->  duplicate
new / triaging            --snooze-->          snoozed
snoozed（snooze_until 已过，读时惰性）          --> new
converted / rejected / duplicate = 终态
accepted = 保留，v0.1 不产出
```

- 可分诊（非终态）集合 = `{new, triaging, snoozed}`；对终态行执行分诊动作抛 `INTAKE_NOT_ACTIONABLE`。
- `triaging` 为可选"处理中"标记，经 PATCH 设置。
- accept 幂等：已 converted / 终态再 accept 抛 `INTAKE_NOT_ACTIONABLE`（叠加 DB 唯一约束兜底）。

## 3. REST API

统一 `Envelope[...]`，schema 继承 `ApiModel`（camelCase + from_attributes），列表 `Page[T]`，查询参数保持 `page` / `page_size`。

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/projects/{project_id}/intake?status=&source=&page=&page_size=` | 请求池分页（状态/来源筛选） | `intake.read` |
| POST | `/api/v1/projects/{project_id}/intake` | 创建请求（manual；同步产建议） | `intake.create` |
| GET | `/api/v1/intake/{id}` | 详情（读时惰性解除过期 snooze） | `intake.read`（资源级 dep） |
| PATCH | `/api/v1/intake/{id}` | 改 title/description（重算建议）/status→triaging | `intake.triage` |
| POST | `/api/v1/intake/{id}/accept` | 接受并转 WorkItem（原子） | `intake.triage` |
| POST | `/api/v1/intake/{id}/reject` | 拒绝（可带 reason） | `intake.triage` |
| POST | `/api/v1/intake/{id}/mark-duplicate` | 标记重复（带 duplicate_work_item_id） | `intake.triage` |
| POST | `/api/v1/intake/{id}/snooze` | 稍后处理（带 snooze_until） | `intake.triage` |

平铺 `/intake/{id}` 路由先解析行的 `project_id` 再做项目级校验（仿 `work_items/deps.py::require_work_item_permission`，404 覆盖不存在/跨 tenant/软删）。router 在 `api.py` 注册一行。

service 函数（`async def fn(db, actor, *, ...)`，审计与业务同事务）：`create_intake_request`、`list_intake_requests`、`get_intake_request`、`update_intake_request`、`accept_intake_request`、`reject_intake_request`、`mark_duplicate`、`snooze_intake_request`。

### 原子 accept-and-convert（需 M3 小重构）

`work_items.service.create_work_item` 当前内部 commit（`service.py:278`）。抽出**无 commit 的 core**，让 intake 在同一事务内组合转换：

```python
# work_items/service.py
async def create_work_item_in_tx(db, actor, project_id, data, *, source, source_ref_id, reporter_id) -> WorkItem:
    # 现 create_work_item 第 240–277 行（flush + activity + audit），无 commit
    return item

async def create_work_item(db, actor, project_id, data, *, source=MANUAL, source_ref_id=None, reporter_id=None) -> WorkItemOut:
    item = await create_work_item_in_tx(db, actor, project_id, data,
                                        source=source, source_ref_id=source_ref_id, reporter_id=reporter_id)
    await db.commit()
    return (await _build_work_item_outs(db, [item]))[0]
```

公开签名不变。`intake.service.accept_intake_request` 调 `create_work_item_in_tx`，再回填 `intake.converted_work_item_id` / `status=converted` + 写 `intake.accept` 审计，最后一次 `db.commit()`。`reporter_id = intake.submitter_id or actor.id`；`type/priority/assignee` 取 overrides → 建议 → 默认。

### 错误码（3xxx，`core/errors.py`）

| 码 | 名 | 触发 |
| --- | --- | --- |
| 3001 | INTAKE_NOT_FOUND | 请求不存在 / 跨 tenant |
| 3002 | INTAKE_NOT_ACTIONABLE | 对终态行（converted/rejected/duplicate）执行分诊动作；重复 accept |
| 3003 | INTAKE_DUPLICATE_TARGET_INVALID | duplicate_work_item_id 不存在/跨项目/已删 |

> snooze_until 非未来时间复用 `INVALID_INPUT=1002`；权限不足复用 `FORBIDDEN=1004`。

## 4. MCP Tools

`modules/intake/mcp.py` 定义 FastMCP 子服务器，`worknexus/mcp.py` `mcp.mount(intake_mcp, namespace="intake")`。tool 内只经 `require_mcp_context()` 取 `(db, actor, delegation)`，统一过 `SkillInvocationMiddleware` 双 token + 风险门禁 + 留痕。

| Tool（namespace 前缀） | 风险 tag | 是否需确认 | 说明 |
| --- | --- | --- | --- |
| `intake_list_intake_requests` | `read` + `perm:intake.read` | 否（直接执行） | 列 delegation 项目内请求（供 AI 分诊参考） |
| `intake_create_intake_request` | `low_write` + `perm:intake.create` | 是（defer→AgentAction） | AI 在 WorkChat 提案建请求；确认后 dispatch 落库 `source=ai_chat` |
| `intake_accept_intake_request` | `low_write` + `perm:intake.triage` | 是（defer→AgentAction） | AI 提案接受并转工作项；确认后 dispatch 调 `intake.service.accept` |

reject / mark-duplicate / snooze **不暴露给 AI**（v0.1 仅人工；只有 create/accept 是 M5 推迟到本期的动作）。

### 接入 M5 AgentAction 确认链（D，直接扩展）

- `workchat/schemas.py` `AgentActionType` 新增 `CREATE_INTAKE_REQUEST = "create_intake_request"`、`ACCEPT_INTAKE_REQUEST = "accept_intake_request"`。
- `workchat/service.py` `_TOOL_TO_ACTION` 新增 `intake_create_intake_request` / `intake_accept_intake_request`；`_ACTION_PERMISSION` 新增 `CREATE_INTAKE_REQUEST→INTAKE_CREATE`、`ACCEPT_INTAKE_REQUEST→INTAKE_TRIAGE`。
- `_dispatch` 拆为 `_dispatch_work_item_action` / `_dispatch_intake_action`；后者 import `intake.service`：
  - `create_intake_request` → `intake.service.create_intake_request(db, ai_actor, action.project_id, ..., source=ai_chat, source_ref_id=action.id, submitter_id=action.requested_by_user_id)`；result_ref = `("intake_request", intake.id)`。
  - `accept_intake_request` → `intake.service.accept_intake_request(db, ai_actor, args["intake_request_id"], overrides)`；result_ref = `("work_item", converted_work_item_id)`，前端确认卡片执行后可直达生成的工作项。
- 身份/作用域**绝不**取自 tool 参数：project 取 `action.project_id`、发起人取 `action.requested_by_user_id`、source 由 service 内部定。
- 依赖方向（无环）：`skills.middleware → workchat.create_pending_agent_action`；`workchat.service → work_items.service`；`workchat.service → intake.service`；`intake.service → work_items.service`；`intake.mcp → intake.service`。

## 5. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/projects/{id}/intake` | 项目 Intake 收件箱 | DataTable（状态/来源筛选）+ 行点开右侧 `IntakeDetailSheet`；抽屉内 `TriageSuggestionCard`（建议性 AI 摘要/分类/类型·优先级，"采纳建议"预填）+ `IntakeTriageActions`（accept 开 `ConvertToWorkItemDialog` 预填→落工作项；reject 经 `ConfirmDialog` + 可选原因；mark-duplicate 工作项选择器 Dialog；snooze 日期选择器 Dialog）；三态 `PageSkeleton/EmptyState/ErrorState`；入口 `PermissionGate permission="intake.read"`（项目详情页按钮 + 路由懒加载于 AppShell/RequireAuth 下） |

- `features/intake/api/`：`intakeKeys` Key Factory；`useIntakeListQuery` / `useIntakeQuery`；`useCreateIntakeMutation` / `useAcceptIntakeMutation` / `useRejectIntakeMutation` / `useMarkDuplicateMutation` / `useSnoozeIntakeMutation` / `usePatchIntakeMutation`（经 contracts client + `unwrap()`；成功按 Key Factory invalidate；需表单内联错误的 mutation 用 `meta.suppressToast` + 3xxx→i18n 映射）。
- `api/schemas.ts`：create / convert 表单 zod schema（react-hook-form + zodResolver + shadcn Form 全链）。
- 组件：`IntakeList`（DataTable，列定义独立 `columns.tsx` 接收 `t`）、`IntakeDetailSheet`、`IntakeTriageActions`、`TriageSuggestionCard`、`ConvertToWorkItemDialog`、`IntakeStatusBadge` + `IntakeSourceBadge`（cva 变体，仅语义 token 类）。AI 文本经 `lib/markdown.tsx` sanitize。
- `lib/paths.ts` 加 `paths.intake(projectId)`。
- i18n namespace：`intake`（zh-CN / en-US 同步，四步注册：`locales/index.ts` + `i18n.ts` `ns`+`AppTFunction` + `i18next.d.ts`）。

i18n namespace：`intake`（zh-CN / en-US 同步提供）

- **§5.5 手册补条**（新场景先补手册再写业务，同步 AGENTS↔CLAUDE）：**建议性 AI 卡片 + 采纳预填**——`TriageSuggestionCard` 呈现只读 advisory 建议（区别于"确认即执行"的 `AgentActionCard`），"采纳建议"将 suggested_* 预填进 `ConvertToWorkItemDialog`，落库仍由用户提交确认。

## 6. 审计与权限点

### 审计事件（`audit.service.AuditAction` 新增，覆盖 spec §8 "Intake 接受/拒绝/重复"）

- `intake.create`：创建请求（manual / ai_chat dispatch）。
- `intake.update`：PATCH 改 title/description/status。
- `intake.accept`：接受并转换（同事务另含既有 `work_item.create`——完整链：intake.accept + work_item.create）。
- `intake.reject` / `intake.duplicate` / `intake.snooze`：对应分诊动作。
- AI 路径可追溯链：`AgentAction.requested_by_user_id` + `agent_id` + `approved_by_user_id` + `skill_invocation_id` + `result_ref`（work_item / intake_request）。

### 权限点（沿用 M1 矩阵，禁改 access.py）

- `intake.read`：查看列表/详情（viewer+，AI Agent 具备）。
- `intake.create`：提交/创建（member+，AI Agent 具备）。
- `intake.triage`：accept / reject / mark-duplicate / snooze / PATCH 分诊编辑（project_admin+，AI Agent 具备）。
- spec §6 的 `intake.accept` / `intake.reject` **收敛进** `intake.triage`，不新增权限点（保持矩阵稳定、不触发 contracts 连锁）。
- 校验唯一入口：REST 走 `require_permission` / 资源级 dep；MCP 提案走中间件 `decide_execution`（基于 `permissions_snapshot.effective`）；执行走 `approve_and_execute` 内实时 `can()`（用户 ∧ Agent）。

## 7. 测试点

- **TriageEngine 单测**：关键词→type/priority/category；`suggested_assignee_id` 校验（无唯一项目成员匹配→null）；provenance 字段齐备。
- **service 状态机单测**（真实 PG + 回滚 fixture）：各转换 + 守卫（终态→`INTAKE_NOT_ACTIONABLE`、duplicate target 非法、重复 accept 幂等、snooze 惰性回 new）；create 同步产建议。
- **accept-convert 原子性**：同一事务创建 WorkItem（`source=intake`、`source_ref_id`）+ 回填 `converted_work_item_id` + `status=converted`；下游失败整体回滚。
- **REST**（`httpx.ASGITransport`）：list/筛选、create（建议存在）、accept→工作项看板可见、reject/duplicate/snooze + 审计行。
- **MCP in-memory `Client(mcp)`**：`intake_create/accept_intake_request` low_write→pending AgentAction（不执行）；read tool 直接执行；双 token 回环（`issue_delegation_token`→`/mcp`→AgentAction）；approve→`intake.service` 执行、result_ref 正确。
- **前端（vitest + msw）**：query/mutation hooks、`TriageSuggestionCard` 采纳预填、状态/来源 Badge、转换表单校验。
- **E2E（Playwright，主链路，`WORKNEXUS_AI_CLIENT=fake`）**：提交 intake → 分诊 → 接受 → 工作项落库（`source=intake`）→ 看板可见；+ 语言/主题切换。
- 覆盖率门槛：后端 service ≥85% / 整体 ≥70%；前端 `lib/` + stores ≥80%。

## 8. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-15 | PR1（设计） | 初版设计：与用户敲定 A–H（A 规则版可替换 `TriageEngine`、advisory 建议带 provenance、不依赖 multirag、`suggested_assignee_id` 校验项目成员；B manual+ai_chat 真接、mcp 预留同 work_items、api/email/IM 占位；C 单步 accept=接受并转换·原子，`accepted` 保留不产出；D 直接扩展 M5 dispatcher 不做 registry，`workchat→intake` 无环；E source/ref id 表达来源、不建 relation 行，`CREATED_FROM_INTAKE` 保留枚举；F DataTable + Sheet 抽屉 + 转换 Dialog；G 3xxx 错误码 + intake.* 审计 + 复用 intake.read/create/triage 权限；H 转化率归 M7、Home 归 M8）；状态机 7 态（accepted 保留）；原子 accept 需 M3 抽 `create_work_item_in_tx` 无 commit core；intake_requests 模型 + `UniqueConstraint(converted_work_item_id)`；5 个 PR 拆分；同步 roadmap M6 进度 |
