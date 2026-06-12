# 开发流程

详细规范见 `AGENTS.md` 第 10 节，本文件是操作手册。

## 会话必读链（强制）

每个开发会话开始：`AGENTS.md`（规范）→ `docs/roadmap.md`（蓝图/进度/决策）→ `docs/modules/<module>.md`（模块细节）。有疑问先与用户讨论敲定，禁止靠假设开发。

## 模块文档驱动开发（强制）

1. 开发任何模块前，复制 `docs/modules/_template.md` 为 `docs/modules/<module>.md`，写清目标、数据模型、API、MCP tools、UI、测试点。
2. 每完成一个 PR，必须在同 PR 内更新对应模块文档的"变更记录"小节。**文档未更新的 PR 视为未完成。**
3. 规范变更（AGENTS.md）必须同提交同步 CLAUDE.md；版本变更必须同步 docs/tech-stack.md。

## 分支与提交

- `main` 为保护分支；功能分支 `feat/<module>-<desc>`，修复分支 `fix/<module>-<desc>`。
- 提交信息遵循 Conventional Commits，**一律使用英文**，scope 用模块名：

```text
feat(work-items): drag cards across board columns with activity logging
fix(intake): mark duplicate requests as duplicate status
docs(skills): update MCP tool risk level notes
```

## PR 规范

一 PR 一意图、标题用 Conventional Commits、squash 合并、描述用 `.github/PULL_REQUEST_TEMPLATE.md` 模板并逐项过自查清单。完整规则见 `AGENTS.md` 10.1。

## 单个功能的标准开发循环

```text
建/更新 docs/modules/<module>.md
  → 后端：models → alembic 迁移 → schemas → service（含审计）→ router + mcp → 模块内测试
  → npm run contracts:generate 同步前端类型
  → 前端：features/<feature>/ 下 api hooks → 组件 → 路由 → 文案（zh-CN + en-US）→ 测试
  → lint + typecheck + 测试全绿
  → PR（含模块文档变更记录）
```

## CI 门禁（建立后逐项启用）

lint → typecheck → i18n 扫描 → 单测 → 覆盖率（后端 ≥70%，service ≥85%；前端 lib/stores ≥80%）→ build → E2E 主链路。
