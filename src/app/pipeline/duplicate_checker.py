import re
import asyncio
from typing import Optional
from pathlib import Path
from app.db.database import DatabaseCoordinator
from app.utils.logging import get_logger

logger = get_logger(__name__)

class DuplicateFilter:
    def __init__(self, db_coordinator: Optional[DatabaseCoordinator] = None, base_output_dir: Optional[str] = None):
        self.db = db_coordinator
        self.base_output_dir = base_output_dir
        self._lock = asyncio.Lock()
        self._in_memory_seen = set()

    @staticmethod
    def normalize_title(title: str) -> str:
        """
        Deterministically normalizes a title for exact duplicate matching.
        1. Lowercases
        2. Replaces hyphens, underscores and special chars with spaces
        3. Removes multiple spaces
        4. Strips leading/trailing spaces
        """
        title = title.lower()
        title = re.sub(r'[^a-z0-9\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()

    def is_duplicate_sync(self, title: str, base_output_dir: Optional[str] = None) -> bool:
        """Checks duplicate status against in-memory history and local disk folders."""
        normalized = self.normalize_title(title)
        if not normalized:
            return True
        if normalized in self._in_memory_seen:
            return True

        target_base = base_output_dir or self.base_output_dir
        if target_base:
            folder_name = re.sub(r'[\s-]+', '_', normalized)
            target_path = Path(target_base) / folder_name
            if target_path.exists():
                return True
        return False

    async def is_duplicate(self, title: str, base_output_dir: Optional[str] = None) -> bool:
        """
        Checks if the exact normalized title already exists in in-memory cache,
        disk folders, or SQLite database.
        Returns True if a duplicate is found, False otherwise.
        """
        normalized = self.normalize_title(title)
        if not normalized:
            return True

        if self.is_duplicate_sync(title, base_output_dir):
            return True

        if self.db:
            async with self._lock:
                try:
                    row = await self.db.fetch_one(
                        "SELECT id FROM generations WHERE normalized_title = ?",
                        (normalized,)
                    )
                    if row is not None:
                        return True
                except Exception as e:
                    logger.warning(f"Error querying SQLite database for duplicate title: {e}")

        return False

    def record(self, title: str):
        """Records a title in the in-memory duplicate filter history."""
        normalized = self.normalize_title(title)
        if normalized:
            self._in_memory_seen.add(normalized)

