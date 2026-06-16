# WorkNexus Web

React frontend for WorkNexus. The app is part of the root npm workspace and should normally be developed
through the root scripts.

## Stack

- React 19 + TypeScript
- Vite
- Tailwind CSS 4 semantic tokens
- shadcn/Radix UI primitives
- react-router
- TanStack Query
- zustand
- typed i18next resources
- Playwright E2E

## Local Development

From the repository root:

```bash
npm install
npm run dev:web
```

The frontend expects `VITE_API_BASE_URL` to point at the backend REST API:

```bash
printf 'VITE_API_BASE_URL=http://localhost:8200/api/v1\n' > apps/web/.env
```

Start the backend separately with:

```bash
npm run dev:server
```

## Commands

| Command                              | Description               |
| ------------------------------------ | ------------------------- |
| `npm run dev --workspace=apps/web`   | Start the Vite dev server |
| `npm run build --workspace=apps/web` | Type-check and build      |
| `npm run lint --workspace=apps/web`  | Run ESLint                |
| `npm run test --workspace=apps/web`  | Run Vitest                |
| `npm run e2e --workspace=apps/web`   | Run Playwright E2E        |

## Project Rules

- Feature code lives under `src/features/<feature>`.
- Shared display components live under `src/components`.
- API calls go through `packages/contracts` and feature query hooks.
- User-visible text must use typed `zh-CN` and `en-US` i18n resources.
- Theme colors must use semantic tokens from `src/styles/globals.css`.
- AI and Markdown content must render through `src/lib/markdown.tsx`.

See the root [README](../../README.md), [AGENTS.md](../../AGENTS.md), and
[docs/roadmap.md](../../docs/roadmap.md) for the full engineering contract.
