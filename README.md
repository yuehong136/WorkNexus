# WorkNexus

<p align="center">
  <strong>AI-native WorkOS for turning AI suggestions into governed team work.</strong>
</p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a>
  ·
  <a href="docs/roadmap.md">Roadmap</a>
  ·
  <a href="docs/reference/v0.1-feature-spec.md">v0.1 Spec</a>
  ·
  <a href="docs/tech-stack.md">Tech Stack</a>
</p>

<p align="center">
  <a href="docs/roadmap.md"><img alt="v0.1 status" src="https://img.shields.io/badge/v0.1-M6%20complete-4f46e5"></a>
  <img alt="React" src="https://img.shields.io/badge/React-19-149eca">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136-009688">
  <img alt="FastMCP" src="https://img.shields.io/badge/FastMCP-3.4-7c3aed">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-17-336791">
  <img alt="License" src="https://img.shields.io/badge/license-not%20declared-lightgrey">
</p>

WorkNexus (智协中枢) is a work operating system for AI-assisted teams. It brings projects, work items,
intake, AI WorkChat, Skills/MCP, permissions, and audit trails into one business data layer.

It is intentionally **not** a model orchestration platform. WorkNexus sits beside the existing AI platform
(`multirag`, default `http://localhost:8123`): multirag handles models, RAG, agents, workflows, MCP client
behavior, and prompts; WorkNexus owns business data, permission checks, human confirmation, execution, and
audit.

> AI can propose actions. WorkNexus validates permissions, asks for human confirmation when required,
> executes through the service layer, and records the full audit chain.

## Current Status

WorkNexus is in active `v0.1` development. The roadmap has progressed through **M6 Intake**; dashboards and
the final settings/audit/home polish are still pending.

| Milestone | Area                                                           | Status      |
| --------- | -------------------------------------------------------------- | ----------- |
| M0        | Monorepo scaffold                                              | Done        |
| M1        | Identity, access control, sessions, invites, delegation tokens | Done        |
| M2        | Project spaces and members                                     | Done        |
| M3        | Work items, Workflow Lite, list, drawer, board                 | Done        |
| M4        | Skills/MCP foundation and invocation logs                      | Done        |
| M5        | AI WorkChat, SSE runs, AgentAction confirmation                | Done        |
| M6        | Intake inbox, triage, accept-to-work-item flow                 | Done        |
| M7        | Project dashboards                                             | Not started |
| M8        | Audit UI, settings polish, home workbench                      | Not started |

The source of truth for scope, decisions, and implementation order is [docs/roadmap.md](docs/roadmap.md).

## What You Can Try

- First-run setup, local login, HttpOnly-cookie sessions, invite links, and member management.
- Project creation, archive flow, project detail, summaries, and project member roles.
- Work item creation, editing, comments, activity timeline, relations, status transitions, and board view.
- WorkNexus `/mcp` business tools with server token + short-lived delegated user identity.
- Skill invocation tracking for MCP calls, including risk level, represented user, and status.
- Project AI WorkChat with streaming responses, proposed actions, and approval/rejection cards.
- Intake inbox with rule-based advisory triage, detail sheet, duplicate/reject/snooze handling, and
  atomic accept-to-work-item conversion.
- Generated TypeScript contracts shared by the React frontend and FastAPI backend.

For offline or deterministic local AI testing, set `WORKNEXUS_AI_CLIENT=fake`. The real multirag adapter is
present, but the live endpoint/body remains a tracked verification item in the WorkChat module notes.

## Why WorkNexus

Most AI work tools stop at chat, retrieval, or workflow orchestration. WorkNexus focuses on the execution
boundary:

| Problem                                             | WorkNexus answer                                                                                            |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| AI suggests work, but business data lives elsewhere | Projects, work items, intake requests, and audit logs are first-class system records                        |
| AI write actions are risky                          | Low-risk writes become `AgentAction` records and require confirmation before execution                      |
| Permissions are easy to bypass in tool calls        | WorkNexus rechecks user permission, AI agent permission, resource scope, risk level, and confirmation state |
| Agent activity is hard to explain later             | Skill invocations, proposed actions, approvals, execution results, and audits are linked                    |
| AI platform boundaries get blurry                   | multirag thinks and orchestrates; WorkNexus validates, confirms, executes, and audits                       |

## AI Safety Model

WorkNexus treats model output and MCP tool calls as untrusted input.

- **AgentAction confirmation flow:** AI-generated writes are recorded as pending actions first; users approve or
  reject them in WorkNexus.
- **Dual-token MCP access:** `/mcp` requires a server token plus `X-WorkNexus-Delegation`, a short-lived token
  that represents the user, agent, project, conversation, and run.
- **Fixed risk levels:** `read`, `low_write`, and `high_write` are shared by MCP tools, AgentActions,
  SkillInvocations, and audit logs.
- **Double-check formula:** execution requires user permission AND AI agent permission AND resource permission
  AND allowed risk level AND valid confirmation state.
- **Service-layer writes:** REST routes and MCP tools stay thin; module services are the write boundary and
  record audit entries in the same transaction.
- **Sanitized AI rendering:** frontend AI/Markdown content is rendered through the project markdown wrapper, not
  raw `dangerouslySetInnerHTML`.

## Architecture

```text
User / Browser
  -> apps/web                 React 19 + Vite + Tailwind CSS 4
  -> apps/server /api/v1      FastAPI REST API
  -> apps/server /mcp         FastMCP business tools
  -> PostgreSQL               system of record

WorkNexus -> multirag         model / RAG / agent orchestration through AI Adapter
multirag  -> WorkNexus /mcp   business tool calls with delegated user identity
```

Repository layout:

```text
apps/
  web/             React frontend workspace
  server/          FastAPI + FastMCP backend managed by uv
packages/
  contracts/       orval-generated API types and client
docs/
  modules/         module design documents and change logs
  roadmap.md       product scope, decisions, and progress
  tech-stack.md    pinned stack and upgrade policy
infra/docker/      local PostgreSQL compose stack
```

## Tech Stack

| Layer         | Stack                                                                                        |
| ------------- | -------------------------------------------------------------------------------------------- |
| Frontend      | React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui, react-router, TanStack Query, zustand |
| Backend       | Python 3.13, FastAPI, FastMCP, Pydantic v2, SQLAlchemy 2 async, Alembic                      |
| Database      | PostgreSQL 17                                                                                |
| API contracts | OpenAPI + orval                                                                              |
| Quality       | ESLint, Prettier, Vitest, Playwright, ruff, mypy, pytest                                     |

See [docs/tech-stack.md](docs/tech-stack.md) for exact version policy and dependency rules.

## Quick Start

### Prerequisites

- Node.js `>=22.12`
- npm `>=10`
- Python `>=3.13`
- uv
- Docker, or another local PostgreSQL 17-compatible instance

### Install

```bash
npm install
cd apps/server && uv sync
```

### Configure

Most local defaults work with the bundled docker compose database. For explicit configuration, copy the shared
example into each app directory:

```bash
cp .env.example apps/server/.env
cp .env.example apps/web/.env
```

Key local defaults:

| Setting     | Default                                                             |
| ----------- | ------------------------------------------------------------------- |
| Frontend    | `http://localhost:5173`                                             |
| REST API    | `http://localhost:8200/api/v1`                                      |
| MCP         | `http://localhost:8200/mcp`                                         |
| PostgreSQL  | `postgresql+asyncpg://worknexus:worknexus@localhost:5432/worknexus` |
| AI platform | `http://localhost:8123`                                             |

For local development without multirag, set this in `apps/server/.env`:

```bash
WORKNEXUS_AI_CLIENT=fake
```

### Run

```bash
# 1. Start PostgreSQL
cd infra/docker
docker compose up -d
cd ../..

# 2. Apply database migrations
cd apps/server
uv run alembic upgrade head
cd ../..

# 3. Start the backend
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
| `npm run e2e`                | Run Playwright E2E tests                                 |

Backend quality commands from `apps/server`:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
```

## Development Contract

WorkNexus uses document-driven development. Every implementation session starts with:

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

For the full engineering contract, read [AGENTS.md](AGENTS.md). `CLAUDE.md` is a synchronized mirror and must
be updated in the same commit whenever `AGENTS.md` changes.

## Documentation

- [Roadmap](docs/roadmap.md): `v0.1` scope, module order, and fixed decisions.
- [Tech stack](docs/tech-stack.md): version baseline and upgrade rules.
- [Development workflow](docs/development-workflow.md): branch, PR, and module workflow.
- [Feature specification](docs/reference/v0.1-feature-spec.md): detailed `v0.1` acceptance scope.
- [Module docs](docs/modules): implementation notes and change logs per module.

## Contributing

This repository currently follows the project-local contribution rules in [AGENTS.md](AGENTS.md) and
[.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

Commit messages use Conventional Commits in English:

```text
feat(work-items): create work item board
fix(identity): expire revoked invite tokens
docs(skills): clarify MCP risk tags
```

## License

No open-source license has been declared yet. Treat the repository as private/internal unless a `LICENSE` file
is added.
