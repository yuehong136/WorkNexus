"""Drop/recreate the e2e database and migrate to head. Run by Playwright globalSetup."""

import asyncio
import os
import subprocess
from pathlib import Path

import asyncpg

E2E_DB = "worknexus_e2e"
BASE_URL = os.environ.get(
    "WORKNEXUS_TEST_DATABASE_URL", "postgresql+asyncpg://worknexus:worknexus@localhost:5432/worknexus_test"
)
ADMIN_DSN = BASE_URL.replace("+asyncpg", "").rsplit("/", 1)[0] + "/postgres"
E2E_URL = BASE_URL.rsplit("/", 1)[0] + f"/{E2E_DB}"
SERVER_DIR = Path(__file__).resolve().parents[1]


async def reset() -> None:
    conn = await asyncpg.connect(ADMIN_DSN)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{E2E_DB}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{E2E_DB}"')
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(reset())
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=SERVER_DIR,
        env={**os.environ, "WORKNEXUS_DATABASE_URL": E2E_URL},
        check=True,
    )
    print(f"e2e database ready: {E2E_URL}")
