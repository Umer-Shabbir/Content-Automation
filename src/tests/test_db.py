import pytest
import pytest_asyncio
import sqlite3
import aiosqlite
import asyncio
import tempfile
import os
from pathlib import Path
from app.db.database import DatabaseCoordinator
from app.pipeline.duplicate_checker import DuplicateFilter

@pytest_asyncio.fixture
async def db_coordinator():
    # Use a temporary file for testing SQLite persistence
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name

    db = DatabaseCoordinator(temp_db_path)
    async with db.get_connection() as conn:
        await conn.execute("""
            CREATE TABLE generations (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                preset_name TEXT NOT NULL,
                title TEXT NOT NULL,
                normalized_title TEXT NOT NULL,
                script TEXT NOT NULL,
                prompts_json TEXT NOT NULL,
                UNIQUE(normalized_title)
            )
        """)
        await conn.commit()
    yield db
    # Cleanup
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)

@pytest.mark.asyncio
async def test_duplicate_filter_normalization():
    df = DuplicateFilter(None)
    assert df.normalize_title("The Fall of Rome!") == "the fall of rome"
    assert df.normalize_title("  the fall    of   r_ome- ") == "the fall of r ome"
    assert df.normalize_title("The-Fall_Of_Rome") == "the fall of rome"

@pytest.mark.asyncio
async def test_duplicate_checking(db_coordinator):
    df = DuplicateFilter(db_coordinator)

    # Insert a dummy record
    async with db_coordinator.get_connection() as conn:
        await conn.execute(
            """INSERT INTO generations (id, job_id, topic, preset_name, title, normalized_title, script, prompts_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("g1", "j1", "Rome", "History", "The Fall of Rome", "the fall of rome", "script", "[]")
        )
        await conn.commit()

    assert await df.is_duplicate("The Fall of Rome") is True
    assert await df.is_duplicate("THE FALL OF ROME!!!") is True
    assert await df.is_duplicate("Rise of Rome") is False
