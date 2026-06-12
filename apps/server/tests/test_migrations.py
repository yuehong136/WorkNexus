"""Alembic migration smoke: upgrade head must work on a pristine database."""

import os
import subprocess
from pathlib import Path

import asyncpg
import pytest

from conftest import TEST_DATABASE_URL

pytestmark = [pytest.mark.p2, pytest.mark.integration]

SCRATCH_DB = "worknexus_test_alembic"
SERVER_DIR = Path(__file__).resolve().parents[1]


def _admin_dsn() -> str:
    # Reuse the test credentials against the maintenance database.
    return TEST_DATABASE_URL.replace("+asyncpg", "").rsplit("/", 1)[0] + "/postgres"


async def test_alembic_upgrade_head_on_fresh_db() -> None:
    admin = await asyncpg.connect(_admin_dsn())
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{SCRATCH_DB}"')
        await admin.execute(f'CREATE DATABASE "{SCRATCH_DB}"')
    finally:
        await admin.close()

    scratch_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + f"/{SCRATCH_DB}"
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=SERVER_DIR,
        env={**os.environ, "WORKNEXUS_DATABASE_URL": scratch_url},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr

    check = await asyncpg.connect(scratch_url.replace("+asyncpg", ""))
    try:
        version = await check.fetchval("SELECT version_num FROM alembic_version")
        tables = {
            r["tablename"] for r in await check.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        }
    finally:
        await check.close()
    assert version is not None
    assert {"tenants", "users", "sessions", "role_bindings", "audit_logs", "projects"} <= tables

    admin = await asyncpg.connect(_admin_dsn())
    try:
        await admin.execute(f'DROP DATABASE "{SCRATCH_DB}"')
    finally:
        await admin.close()
