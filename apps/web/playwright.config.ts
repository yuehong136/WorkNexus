import { defineConfig } from '@playwright/test'

// E2E runs against an isolated database and its own ports so a running dev
// stack (5173/8200, dev DB) is never touched. PostgreSQL must be running;
// the globalSetup script drops/recreates worknexus_e2e and migrates it.
const E2E_DATABASE_URL = 'postgresql+asyncpg://worknexus:worknexus@localhost:5432/worknexus_e2e'
const API_PORT = 8201
const WEB_PORT = 5174

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 60_000,
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
  },
  webServer: [
    {
      command: `uv run uvicorn worknexus.main:app --port ${API_PORT}`,
      cwd: '../server',
      url: `http://localhost:${API_PORT}/api/v1/health`,
      env: {
        WORKNEXUS_DATABASE_URL: E2E_DATABASE_URL,
        WORKNEXUS_CORS_ORIGINS: `["http://localhost:${WEB_PORT}"]`,
      },
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `npm run dev -- --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: {
        VITE_API_BASE_URL: `http://localhost:${API_PORT}/api/v1`,
      },
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
})
