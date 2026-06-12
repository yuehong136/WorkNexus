# 任务派发提示词模板

> 用途：向一个没有任何上下文的 AI 开发会话派发任务时，复制下方模板、填写"本次任务"部分即可。
> 模板刻意精简：所有重内容都在仓库文档里，提示词只负责引导阅读顺序和压住工作铁律。

---

```text
你正在 WorkNexus 项目工作（路径：/Users/dxl/project/WorkNexus）。
这是一个 AI-native 团队协作与工单 WorkOS，monorepo：
- apps/web：React 19 + Vite 8 + Tailwind 4 + shadcn/ui（feature 切片）
- apps/server：FastAPI + FastMCP 模块化单体（REST /api/v1 + MCP /mcp）
- packages/contracts：orval 从后端 OpenAPI 生成的契约

【开工前必读，按顺序，不可跳过】
1. AGENTS.md —— 工程规范唯一真相源（技术栈定版、目录分层、统一写法手册 5.5/5.6、
   i18n/主题铁律、AI 安全规范、测试与 PR 规范）
2. docs/roadmap.md —— 全局蓝图、模块进度（第 3 节）、已敲定决策 D1–D8（第 4 节）
3. 本次任务涉及的 docs/modules/<module>.md；不存在则从 _template.md 创建，
   这本身就是开发的第一步

【工作铁律】
- 读完文档后，对范围、设计、字段、交互、对接细节有任何疑问，必须先与我讨论
  敲定再动手，禁止靠假设开发；roadmap 的范围与决策变更必须经我确认
- 同场景只允许一种写法：对齐 AGENTS.md 5.5/5.6 统一写法手册；手册未覆盖的
  新场景，先在同一 PR 补手册条目再写业务代码
- 文案必须 zh-CN / en-US 双语齐备，禁止任何硬编码文案与裸色值
- git 提交一律英文 Conventional Commits；一 PR 一意图；生成产物单独 commit；
  接口变更后运行 npm run contracts:generate
- 完成标准：lint / typecheck / 测试全绿 + 模块文档变更记录已追加 +
  roadmap 进度已更新；规范文件变更必须同步 CLAUDE.md

【本次任务】
目标：<一句话说清要做什么>
涉及模块：<如 M1 identity / M3 work_items；新模块请注明>
验收标准：<完成后能演示/验证什么>
特殊约束或上下文：<可选：本次的特殊要求、已有讨论结论、参考资料>
```

---

## 使用建议

- "本次任务"四个字段尽量填实：目标越具体，无上下文会话提问越少、返工越少。
- 跨多个模块的大任务，建议拆成多次派发（一 PR 一意图）。
- 若任务涉及 multirag 对接，补充说明 multirag 侧的可用资源（agent_id、API key 是否已配置等）。
- 若上一个会话有未完成的讨论结论，把结论粘进"特殊约束或上下文"，不要假设新会话能看到历史聊天。
