# 模块：scaffold（项目脚手架）

> 状态：开发中
> 负责人：dxl
> 关联 feature（前端）：`apps/web`（应用骨架，非单一 feature）
> 关联 module（后端）：`apps/server/src/worknexus`（应用骨架，非单一 module）

## 1. 目标与范围

把 monorepo 从"规范基线"推进到"可运行骨架"：前端可启动并展示带主题/i18n 的 AppShell，后端同进程提供 REST（`/api/v1`）与 MCP（`/mcp`）并连通 PostgreSQL，契约生成管线可用。

不做：任何业务模块（projects、work_items 等后续各自建模块文档）；认证完整实现（仅留 Actor 依赖桩）；CI 工作流。

## 2. 数据模型

无业务模型。仅建立：

| 内容 | 说明 |
| --- | --- |
| `db.py` Base + mixin | `id`（uuid 字符串）、`created_at`、`updated_at`、`tenant_id` 预留 |
| Alembic 基线 | 空基线迁移，验证迁移管线可用 |

## 3. REST API

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | 健康检查（含 DB 连通性） | 公开 |

## 4. MCP Tools

| Tool（含 namespace 前缀） | 风险 tag | 是否需确认 | 说明 |
| --- | --- | --- | --- |
| `system_ping` | read | 否 | MCP 连通性验证 |

## 5. UI / 页面

| 路由 | 页面 | 关键交互 |
| --- | --- | --- |
| `/` | 工作台占位页 | AppShell（侧边导航 + 顶栏）、主题切换、语言切换 |

i18n namespace：`common`（zh-CN / en-US）

## 6. 审计与权限点

- 审计事件：无（骨架阶段）
- 权限点：`get_current_actor` 依赖桩（开发期返回固定 dev 用户）

## 7. 测试点

- service 单测：无业务 service
- MCP in-memory 测试：`system_ping` 经 `Client(mcp)` 调通
- 后端冒烟：`GET /api/v1/health` 返回 Envelope `code=0`
- 前端测试：`cn()` / ui store 单测；build + lint 通过

## 8. 变更记录（每个 PR 必须追加一行）

| 日期 | PR | 变更摘要 |
| --- | --- | --- |
| 2026-06-12 | scaffold | 初始化前后端骨架、PostgreSQL compose、contracts 管线 |
| 2026-06-13 | fix | 开发环境 CORS 放行 localhost/127.0.0.1/私网段任意端口（生产仍走 cors_origins 白名单）；前端 API 默认地址跟随页面主机名（局域网免配置）；dev server 监听 0.0.0.0；E2E 端口挪至 8211/5183 避开开发栈 |
