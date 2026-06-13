# WorkNexus

[English](README.md) | [简体中文](README.zh-CN.md)

WorkNexus（智协中枢）is an AI-native WorkOS for team collaboration, work items, intake, AI-assisted work chat, Skills/MCP, permissions, and audit trails.

It is not another model orchestration platform. WorkNexus owns the business data, permission checks, human confirmation, execution, and audit record; the existing AI platform (`multirag`, default `http://localhost:8123`) owns models, RAG, agent orchestration, workflow orchestration, MCP client behavior, and prompts.

> AI can propose actions. WorkNexus validates permissions, asks for human confirmation when required, executes through the service layer, and records the full audit chain.

## Status

WorkNexus is in active `v0.1` development.

| Area                                                                     | Status            |
| ------------------------------------------------------------------------ | ----------------- |
| Monorepo scaffold                                                        | Done              |
| Identity, session, access control, invites, delegation token foundation  | Done              |
| Projects, work items, Skills/MCP, WorkChat, Intake, dashboards, audit UI | Planned in `v0.1` |

The source of truth for roadmap scope and implementation order is [docs/roadmap.md](docs/roadmap.md).

## Highlights

- Project and work-item data model designed for AI-assisted execution, not just chat.
- Server-side session with HttpOnly cookies; no session token in browser storage.
- Fixed RBAC baseline with tenant and project scopes.
- MCP endpoint exposed by WorkNexus for business tools, with server token plus short-lived delegation token.
- AgentAction confirmation flow for AI-generated write actions.
- Full audit requirements for work-item changes, AI suggestions, confirmations, Skill invocations, permission changes, and sensitive operations.
- OpenAPI-generated TypeScript contracts shared by the frontend.

## Architecture

```text
User / Browser
  -> apps/web                 React 19 + Vite + Tailwind 4
  -> apps/server /api/v1      FastAPI REST API
  -> apps/server /mcp         FastMCP business tools
  -> PostgreSQL               system of record

WorkNexus -> multirag         AI adapter call for model / RAG / agent orchestration
multirag  -> WorkNexus /mcp   MCP tool calls with delegated user identity
```

Repository layout:

```text
apps/
  web/             React frontend workspace
  server/          FastAPI + FastMCP backend managed by uv
packages/
  contracts/       orval-generated API types and client
docs/
  modules/         module design documents
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

See [docs/tech-stack.md](docs/tech-stack.md) for exact version policy.

## Getting Started

### Prerequisites

- Node.js `>=22.12`
- npm `>=10`
- Python `>=3.13`
- uv
- Docker or another local PostgreSQL 17-compatible instance

### Install Dependencies

```bash
npm install
cd apps/server && uv sync
```

### Configure Environment

Most local defaults work out of the box with the bundled docker compose database.

For explicit configuration, copy the example file into the app that needs it:

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

### Start Locally

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

Open `http://localhost:5173`. On a fresh database, complete the `/setup` flow first.

## Scripts

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

Backend quality commands can be run from `apps/server`:

```bash
uv run ruff check .
uv run ruff format .
uv run mypy
uv run pytest
```

## Development Rules

WorkNexus uses document-driven development. Every development session starts with:

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

For the full engineering contract, read [AGENTS.md](AGENTS.md). `CLAUDE.md` is a synchronized mirror and must be updated in the same commit whenever `AGENTS.md` changes.

## Documentation

- [Roadmap](docs/roadmap.md): `v0.1` scope, module order, and fixed decisions.
- [Tech stack](docs/tech-stack.md): version baseline and upgrade rules.
- [Development workflow](docs/development-workflow.md): branch, PR, and module workflow.
- [Feature specification](docs/reference/v0.1-feature-spec.md): detailed `v0.1` acceptance scope.
- [Module docs](docs/modules): implementation notes and change logs per module.

## Contributing

This repository currently follows the project-local contribution rules in [AGENTS.md](AGENTS.md) and [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

Commit messages use Conventional Commits in English:

```text
feat(work-items): create work item board
fix(identity): expire revoked invite tokens
docs(skills): clarify MCP risk tags
```

## License

No open-source license has been declared yet. Treat the repository as private/internal unless a LICENSE file is added.
