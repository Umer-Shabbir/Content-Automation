import aiosqlite
import sqlite3
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

class DatabaseCoordinator:
    def __init__(self, db_path: str = "sqlite.db"):
        self.db_path = db_path

    async def initialize(self):
        # Create database file and initialize schema
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            if SCHEMA_PATH.exists():
                with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                    script = f.read()
                    await db.executescript(script)
            await db.commit()

    def get_connection(self):
        """Returns an aiosqlite connection context manager."""
        return aiosqlite.connect(self.db_path)

    async def execute(self, query: str, parameters: tuple = ()) -> None:
        async with self.get_connection() as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute(query, parameters)
            await db.commit()

    async def fetch_one(self, query: str, parameters: tuple = ()) -> Optional[aiosqlite.Row]:
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")
            async with db.execute(query, parameters) as cursor:
                return await cursor.fetchone()

    async def fetch_all(self, query: str, parameters: tuple = ()) -> List[aiosqlite.Row]:
        async with self.get_connection() as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON;")
            async with db.execute(query, parameters) as cursor:
                return await cursor.fetchall()
