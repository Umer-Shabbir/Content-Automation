import re
import asyncio
from typing import Optional
from app.db.database import DatabaseCoordinator
from app.utils.logging import get_logger

logger = get_logger(__name__)

class DuplicateFilter:
    def __init__(self, db_coordinator: DatabaseCoordinator):
        self.db = db_coordinator
        self._lock = asyncio.Lock()

    @staticmethod
    def normalize_title(title: str) -> str:
        """
        Deterministically normalizes a title for exact duplicate matching.
        1. Lowecases
        2. Replaces hyphens, underscores and special chars with spaces
        3. Removes multiple spaces
        4. Strips leading/trailing spaces
        """
        title = title.lower()
        title = re.sub(r'[^a-z0-9\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()

    async def is_duplicate(self, title: str) -> bool:
        """
        Checks if the exact normalized title already exists in the SQLite database.
        Returns True if a duplicate is found, False otherwise.
        """
        normalized = self.normalize_title(title)
        if not normalized:
            return True # Empty titles are treated as duplicates/invalid

        async with self._lock:
            # Query the database to check if normalzied title is present
            row = await self.db.fetch_one(
                "SELECT id FROM generations WHERE normalized_title = ?",
                (normalized,)
            )
            return row is not None
