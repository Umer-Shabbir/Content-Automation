import aiosqlite
import sqlite3
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
# Default persistent database location in Content Automation root
DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[3] / "ideas.db")


class DatabaseCoordinator:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def initialize_sync(self):
        """Synchronously initializes database file and schema using sqlite3."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            if SCHEMA_PATH.exists():
                with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            conn.commit()

    async def initialize(self):
        """Asynchronously initializes database file and schema using aiosqlite."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.execute("PRAGMA journal_mode = WAL;")
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

    def execute_sync(self, query: str, parameters: tuple = ()) -> None:
        """Executes a query synchronously."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(query, parameters)
            conn.commit()

    def fetch_one_sync(self, query: str, parameters: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetches one row synchronously."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            cur = conn.cursor()
            cur.execute(query, parameters)
            return cur.fetchone()

    def fetch_all_sync(self, query: str, parameters: tuple = ()) -> List[sqlite3.Row]:
        """Fetches all rows synchronously."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            cur = conn.cursor()
            cur.execute(query, parameters)
            return cur.fetchall()
