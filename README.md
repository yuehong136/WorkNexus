# WorkNexus

<p align="center">
  <strong>AI-native WorkOS for governed team execution.</strong>
</p>

<p align="center">
  Turn AI suggestions into permission-checked, human-confirmed, fully audited work.
</p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a>
  ·
  <a href="docs/roadmap.md">Roadmap</a>
  ·
  <a href="docs/reference/v0.1-feature-spec.md">v0.1 Spec</a>
  ·
  <a href="docs/tech-stack.md">Tech Stack</a>
  ·
  <a href="docs/development-workflow.md">Development</a>
</p>

<p align="center">
  <a href="docs/roadmap.md"><img alt="v0.1 status" src="https://img.shields.io/badge/v0.1-complete-22c55e"></a>
  <img alt="React" src="https://img.shields.io/badge/React-19-149eca">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136-009688">
  <img alt="FastMCP" src="https://img.shields.io/badge/FastMCP-3.4-7c3aed">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-17-336791">
  <img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-blue">
</p>

WorkNexus (智协中枢) is an AI-native team collaboration and work management WorkOS. It brings projects,
work items, intake, AI WorkChat, Skills/MCP, dashboards, permissions, and audit trails into one business
data layer.

WorkNexus is intentionally **not** a model orchestration platform. It sits beside the existing AI platform
(`multirag`): multirag owns models, RAG, agents, workflows, MCP client behavior, and prompts; WorkNexus owns
business data, permission checks, human confirmation, execution, and audit.

> AI can propose actions. WorkNexus decides whether they are allowed, confirms them with a human when
> required, executes through the service layer, and records the full chain.

## Why WorkNexus

Most AI work tools stop at chat, retrieval, or workflow orchestration. WorkNexus focuses on the execution
boundary where AI output becomes real business state.

| Problem                                      | WorkNexus answer                                                                                            |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| AI suggests work, but records live elsewhere | Projects, work items, intake requests, agent actions, and audits are first-class records                    |
| Tool calls can bypass product permissions    | Every execution rechecks user permission, AI agent permission, resource scope, risk, and confirmation state |
| AI writes are risky by default               | Low-risk writes become pending `AgentAction` records before users approve or reject them                    |
| Agent behavior is hard to explain later      | Skill invocations, proposals, approvals, execution results, and audit logs are linked                       |
| AI platform boundaries get blurry            | multirag thinks and orchestrates; WorkNexus validates, confirms, executes, and audits                       |

## v0.1 Status

`v0.1` is complete. The main acceptance loop is implemented end to end:

```text
/setup -> login -> project -> work item -> board transition -> AI WorkChat
  -> proposed AgentAction -> user approval -> database write
  -> skill_invocations -> audit_logs -> dashboard and home updates
```

The latest roadmap entry records the completed M8 stack with backend, frontend, and Playwright E2E coverage.
Use [docs/roadmap.md](docs/roadmap.md) as the source of truth for scope and progress.

| Milestone | Area                                                  | v0.1     |
| --------- | ----------------------------------------------------- | -------- |
| M0        | Monorepo scaffold                                     | Complete |
| M1        | Identity, sessions, RBAC, invites, delegation tokens  | Complete |
| M2        | Projects and members                                  | Complete |
| M3        | Work items, Workflow Lite, comments, relations, board | Complete |
| M4        | Skills/MCP foundation and invocation logs             | Complete |
| M5        | AI WorkChat, SSE runs, AgentAction confirmation       | Complete |
| M6        | Intake inbox, triage, accept-to-work-item flow        | Complete |
| M7        | Project dashboards and rule-based AI insights         | Complete |
| M8        | Audit UI, Settings Lite, Home workbench               | Complete |

## Core Features

- **Project WorkOS:** project spaces, project members, role-aware access, summaries, and archive flow.
- **Work items:** task, requirement, bug, risk, decision, approval, incident, and feedback records with fixed
  workflow states, comments, activity timeline, relations, custom fields, list view, drawer, and board.
- **Intake:** inbox, deterministic triage suggestions, detail sheet, duplicate/reject/snooze handling, and
  atomic accept-to-work-item conversion.
- **AI WorkChat:** project-scoped conversations, streaming SSE runs, proposed actions, approval/rejection
  cards, and deterministic fake AI mode for local development.
- **Skills/MCP:** FastMCP business tools with read/low-write risk tags, dual-token access, delegation context,
  and full invocation logging.
- **Dashboards:** status/type/priority/source distributions, workload, overdue items, 7-day trends, intake
  conversion, and rule-based AI insight cards.
- **Audit and Home:** tenant-level audit search with AI chain drill-down, settings with masked AI connection
  details, and a cross-project workbench for todos, overdue items, pending AI actions, recent AI-created work,
  and pending intake.
- **Contracts-first frontend:** OpenAPI-generated TypeScript client, TanStack Query hooks, typed i18n resources,
  Tailwind 4 semantic tokens, and a small shadcn/Radix component layer.

## AI Safety Model

WorkNexus treats model output and MCP tool calls as untrusted input.

- **AgentAction confirmation flow:** AI-generated writes are persisted as pending actions first. Users approve
  or reject them inside WorkNexus.
- **Dual-token MCP access:** `/mcp` requires a server bearer token plus `X-WorkNexus-Delegation`, a short-lived
  delegated user token bound to tenant, user, agent, project, conversation, and run.
- **Fixed risk levels:** `read`, `low_write`, and `high_write` are shared by MCP tools, AgentActions,
  SkillInvocations, and audit logs.
- **Execution formula:** user permission AND AI agent permission AND resource permission AND allowed risk level
  AND valid confirmation state.
- **Service-layer writes:** REST routes and MCP tools stay thin. Domain services are the write boundary and
  write audit entries in the same transaction.
- **Sanitized AI rendering:** AI and Markdown content goes through the project markdown wrapper and DOMPurify,
  never raw `dangerouslySetInnerHTML`.

## Architecture

```text
Browser
  -> apps/web                  React 19 + Vite + Tailwind CSS 4
  -> apps/server /api/v1       FastAPI REST API
  -> apps/server /mcp          FastMCP business tools
  -> PostgreSQL                system of record

WorkNexus -> multirag          model / RAG / agent orchestration through AI Adapter
multirag  -> WorkNexus /mcp    business tool calls with delegated user identity
```

Repository layout:

```text
apps/
  web/                         React frontend workspace
  server/                      FastAPI + FastMCP backend managed by uv
packages/
  contracts/                   orval-generated API types and client
docs/
  modules/                     module design documents and change logs
  roadmap.md                   product scope, decisions, and progress
  tech-stack.md                pinned stack and upgrade policy
infra/docker/                  local PostgreSQL compose stack
```

## Tech Stack

| Layer     | Stack                                                                                        |
| --------- | -------------------------------------------------------------------------------------------- |
| Frontend  | React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui, react-router, TanStack Query, zustand |
| Backend   | Python 3.13, FastAPI, FastMCP, Pydantic v2, SQLAlchemy 2 async, Alembic                      |
| Database  | PostgreSQL 17                                                                                |
| Contracts | OpenAPI + orval                                                                              |
| Quality   | ESLint, Prettier, Vitest, Playwright, ruff, mypy, pytest                                     |

Exact version policy and dependency rules live in [docs/tech-stack.md](docs/tech-stack.md).

## Quick Start

### Prerequisites

- Node.js `>=22.12`
- npm `>=10`
- Python `>=3.13`
- uv
- Docker, or another local PostgreSQL 17-compatible instance

### 1. Install dependencies

```bash
npm install
cd apps/server && uv sync
cd ../..
```

### 2. Configure local environment

```bash
cp .env.example apps/server/.env
printf 'VITE_API_BASE_URL=http://localhost:8200/api/v1\n' > apps/web/.env
```

For offline development without a live multirag instance, set this in `apps/server/.env`:

```bash
WORKNEXUS_AI_CLIENT=fake
```

Before using the real multirag adapter, replace the AI platform URL, API key, default external agent id, and MCP
server token in `apps/server/.env` with environment-specific values.

### 3. Start PostgreSQL and migrate

```bash
cd infra/docker
docker compose up -d
cd ../..

cd apps/server
uv run alembic upgrade head
cd ../..
```

### 4. Start the app

```bash
npm run dev:server
```

In another terminal:

```bash
npm run dev:web
```

Open `http://localhost:5173`. On a fresh database, complete `/setup` first.

## Common Commands

| Command                      | Description                                              |
| ---------------------------- | -------------------------------------------------------- |
| `npm run dev:web`            | Start the Vite frontend                                  |
| `npm run build:web`          | Type-check and build the frontend                        |
| `npm run lint:web`           | Run frontend linting                                     |
| `npm run test:web`           | Run frontend unit tests                                  |
| `npm run dev:server`         | Start FastAPI and FastMCP on port `8200`                 |
| `npm run test:server`        | Run backend tests                                        |
| `npm run contracts:generate` | Refresh OpenAPI JSON and regenerate `packages/contracts` |
| `npm run e2e`                | Run Playwright E2E tests against an isolated database    |

Backend quality commands from `apps/server`:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
```

## Documentation

- [Roadmap](docs/roadmap.md): v0.1 scope, module order, fixed decisions, and progress.
- [Feature specification](docs/reference/v0.1-feature-spec.md): detailed v0.1 acceptance scope.
- [Tech stack](docs/tech-stack.md): pinned versions and upgrade rules.
- [Development workflow](docs/development-workflow.md): branch, PR, and module workflow.
- [Module docs](docs/modules): implementation notes and change logs per module.
- [Engineering contract](AGENTS.md): the repository rules for human and AI contributors.

## Development Contract

Every implementation session starts with:

1. [AGENTS.md](AGENTS.md)
2. [docs/roadmap.md](docs/roadmap.md)
3. The relevant `docs/modules/<module>.md`

Key rules:

- Backend writes go through module `service.py`; REST routers and MCP tools stay thin.
- REST responses use the single Envelope shape: `{ "code": 0, "message": "ok", "data": ... }`.
- Frontend requests go through generated contracts and TanStack Query hooks.
- User-visible frontend text must be typed i18n resources in both `zh-CN` and `en-US`.
- Theme values must use semantic Tailwind tokens, not raw color classes.
- AI write actions must go through AgentAction confirmation and audit.

`CLAUDE.md` is a synchronized mirror of `AGENTS.md` and must be updated in the same commit whenever
`AGENTS.md` changes.

## Roadmap

v0.1 delivers the governed AI work loop. Planned follow-up themes include work item enhancements, configurable
workflow, richer intake channels, AI tables/data apps, dashboard builder, docs/knowledge/meeting workflows,
cycles/roadmaps, enterprise permissions, and the broader Agentic WorkOS direction.

See [docs/roadmap.md](docs/roadmap.md) for the full v0.2-v1.0 route.

## Contributing

This repository follows the project-local contribution rules in [AGENTS.md](AGENTS.md) and
[.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

Commit messages use Conventional Commits in English:

```text
feat(work-items): create work item board
fix(identity): expire revoked invite tokens
docs(skills): clarify MCP risk tags
```

## License

WorkNexus is licensed under the [Apache License 2.0](LICENSE), following the same license family used by
RAGFlow.
