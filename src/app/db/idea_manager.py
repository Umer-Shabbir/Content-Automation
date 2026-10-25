import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import List, Optional, Set, Dict, Any, Tuple

from app.db.database import DatabaseCoordinator, DEFAULT_DB_PATH
from app.utils.logging import get_logger

logger = get_logger(__name__)

STOPWORDS = {
    "the", "a", "an", "of", "and", "in", "to", "for", "about",
    "how", "why", "what", "is", "are", "was", "were", "on", "at",
    "by", "from", "with", "story", "explained", "edition"
}


def normalize_topic_string(text: str) -> str:
    """Normalizes a topic or title into lowercase alphanumeric tokens joined by single spaces."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    tokens = text.split()
    return " ".join(tokens)


def extract_keywords(text: str) -> Set[str]:
    """Extracts significant keywords from a topic or title for semantic overlap matching."""
    norm = normalize_topic_string(text)
    tokens = norm.split()
    return {t for t in tokens if t not in STOPWORDS and len(t) >= 2}


class IdeaManager:
    """
    Persistent Idea Manager and Database Coordinator.
    Ensures that once a topic or core idea (e.g. Golden Gate Bridge, Y2K Bug)
    has been generated, it is NEVER generated again.
    """

    def __init__(self, db_coordinator: Optional[DatabaseCoordinator] = None):
        self.db = db_coordinator or DatabaseCoordinator()
        self._lock = threading.Lock()
        self._memory_cache: Set[str] = set()
        self._keyword_cache: List[Tuple[str, Set[str]]] = []  # [(normalized_topic, keywords_set)]
        self._initialized = False

    def initialize(self, extra_scan_dirs: Optional[List[str]] = None):
        """Initializes database schema and loads/syncs existing ideas from database and disk."""
        with self._lock:
            if self._initialized:
                return

            self.db.initialize_sync()
            self._load_from_db()
            self._sync_default_disk_directories(extra_scan_dirs)
            self._initialized = True
            logger.info(f"IdeaManager initialized with {len(self._memory_cache)} unique generated ideas.")

    def _load_from_db(self):
        """Loads all generated and reserved ideas from SQLite into memory cache."""
        try:
            rows = self.db.fetch_all_sync(
                "SELECT normalized_topic, normalized_title, topic FROM generated_ideas"
            )
            for r in rows:
                norm_top = r["normalized_topic"]
                if norm_top:
                    self._memory_cache.add(norm_top)
                    self._keyword_cache.append((norm_top, extract_keywords(norm_top)))

                norm_tit = r["normalized_title"]
                if norm_tit:
                    self._memory_cache.add(norm_tit)
                    self._keyword_cache.append((norm_tit, extract_keywords(norm_tit)))
        except Exception as e:
            logger.warning(f"Failed to load ideas from SQLite: {e}")

    def _sync_default_disk_directories(self, extra_dirs: Optional[List[str]] = None):
        """Automatically scans known content output folders and registers all historical projects."""
        scan_roots = [
            r"H:\Automation\Generated Content",
            r"H:\Automation\Old GenCon",
            r"H:\Automation\output",
        ]
        if extra_dirs:
            for ed in extra_dirs:
                if ed and ed not in scan_roots:
                    scan_roots.append(ed)

        for root in scan_roots:
            p = Path(root)
            if not p.exists() or not p.is_dir():
                continue

            for item in p.iterdir():
                if not item.is_dir():
                    continue

                # Check if this folder represents a project
                meta_file = item / "project.json"
                if not meta_file.exists():
                    meta_file = item / "metadata.json"

                topic = ""
                title = ""
                preset = "unknown"

                if meta_file.exists():
                    try:
                        data = json.loads(meta_file.read_text(encoding="utf-8"))
                        topic = data.get("topic", "")
                        title = data.get("title", "")
                        preset = data.get("preset", "unknown")
                    except Exception:
                        pass

                if not topic:
                    # Deriving from folder name
                    raw_name = item.name.replace("_", " ")
                    topic = raw_name

                self._record_idea_internal(
                    preset_name=preset,
                    topic=topic,
                    title=title,
                    source="disk_scan",
                    status="COMPLETED",
                    output_dir=str(item)
                )

    def is_idea_generated(self, topic_or_title: str) -> bool:
        """
        Determines if a topic or title represents an idea that has already been generated.
        Uses exact normalized match as well as semantic keyword containment.
        E.g. 'golden gate bridge' matches 'The Engineering of the Golden Gate Bridge'.
             'y2k bug' matches 'The Y2K Bug Code Remediation Effort'.
        """
        if not topic_or_title or not topic_or_title.strip():
            return False

        norm = normalize_topic_string(topic_or_title)
        if not norm:
            return False

        with self._lock:
            # 1. Exact match in memory cache
            if norm in self._memory_cache:
                return True

            # 2. Check keyword containment and significant overlap
            cand_kws = extract_keywords(norm)
            if not cand_kws:
                return False

            for existing_norm, existing_kws in self._keyword_cache:
                if not existing_kws:
                    continue

                # Exact substring match in normalized strings
                if norm in existing_norm or existing_norm in norm:
                    return True

                # Overlap calculation
                overlap = cand_kws.intersection(existing_kws)
                if not overlap:
                    continue

                # If candidate's core keywords are entirely contained in existing (e.g. {"golden", "gate", "bridge"})
                if cand_kws.issubset(existing_kws) and len(cand_kws) >= 2:
                    return True

                # If existing's core keywords are entirely contained in candidate
                if existing_kws.issubset(cand_kws) and len(existing_kws) >= 2:
                    return True

                # High Jaccard similarity (>= 0.70)
                union = cand_kws.union(existing_kws)
                if union and (len(overlap) / len(union)) >= 0.70:
                    return True

        return False

    def reserve_idea(self, preset_name: str, topic: str, source: str = "preset_pool") -> bool:
        """
        Reserves an idea before generation begins to prevent race conditions.
        Returns True if reservation succeeded, False if idea was already generated or reserved.
        """
        if self.is_idea_generated(topic):
            return False

        with self._lock:
            norm_topic = normalize_topic_string(topic)
            try:
                self.db.execute_sync(
                    """
                    INSERT INTO generated_ideas (preset_name, topic, normalized_topic, source, status)
                    VALUES (?, ?, ?, ?, 'RESERVED')
                    ON CONFLICT(normalized_topic) DO UPDATE SET status='RESERVED'
                    """,
                    (preset_name, topic, norm_topic, source)
                )
                self._memory_cache.add(norm_topic)
                self._keyword_cache.append((norm_topic, extract_keywords(norm_topic)))
                return True
            except Exception as e:
                logger.warning(f"Error reserving idea '{topic}': {e}")
                return False

    def complete_idea(self, topic: str, title: str = "", output_dir: str = "", preset_name: str = ""):
        """Marks a generated idea as completed with title and output directory."""
        with self._lock:
            self._record_idea_internal(
                preset_name=preset_name or "unknown",
                topic=topic,
                title=title,
                source="pipeline",
                status="COMPLETED",
                output_dir=output_dir
            )

    def release_idea(self, topic: str):
        """Releases a reserved idea if generation fails or is aborted so it can be re-attempted."""
        with self._lock:
            norm_topic = normalize_topic_string(topic)
            if not norm_topic:
                return
            try:
                self.db.execute_sync(
                    "DELETE FROM generated_ideas WHERE normalized_topic = ? AND status = 'RESERVED'",
                    (norm_topic,)
                )
                self._memory_cache.discard(norm_topic)
                self._keyword_cache = [(nt, kw) for nt, kw in self._keyword_cache if nt != norm_topic]
                logger.info(f"Released reservation for topic '{topic}'")
            except Exception as e:
                logger.warning(f"Error releasing idea '{topic}': {e}")

    def _record_idea_internal(
        self,
        preset_name: str,
        topic: str,
        title: str = "",
        source: str = "preset_pool",
        status: str = "COMPLETED",
        output_dir: str = ""
    ):
        """Internal helper to insert/update idea in DB and cache."""
        norm_topic = normalize_topic_string(topic)
        norm_title = normalize_topic_string(title) if title else ""
        if not norm_topic:
            return

        try:
            self.db.execute_sync(
                """
                INSERT INTO generated_ideas (preset_name, topic, normalized_topic, title, normalized_title, source, output_dir, status, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(normalized_topic) DO UPDATE SET
                    title=coalesce(excluded.title, generated_ideas.title),
                    normalized_title=coalesce(excluded.normalized_title, generated_ideas.normalized_title),
                    output_dir=coalesce(excluded.output_dir, generated_ideas.output_dir),
                    status=excluded.status,
                    completed_at=CURRENT_TIMESTAMP
                """,
                (preset_name, topic, norm_topic, title, norm_title, source, output_dir, status)
            )
            self._memory_cache.add(norm_topic)
            self._keyword_cache.append((norm_topic, extract_keywords(norm_topic)))
            if norm_title:
                self._memory_cache.add(norm_title)
                self._keyword_cache.append((norm_title, extract_keywords(norm_title)))
        except Exception as e:
            logger.warning(f"Error saving idea to SQLite: {e}")

    def get_next_topics_for_preset(self, preset_slug: str, preset_obj: Any, count: int = 1) -> List[str]:
        """
        Returns `count` unique topics for the preset that have NEVER been generated before.
        Selects from preset's niche topics pool, filtering out all previously generated topics,
        and automatically reserves them immediately.
        """
        selected: List[str] = []
        niche_pool = getattr(preset_obj, "niche_topics", []) if preset_obj else []

        # 1. Filter out already generated topics from the pool
        candidate_topics = [t for t in niche_pool if not self.is_idea_generated(t)]

        # 2. Pick available candidates and reserve them
        for topic in candidate_topics:
            if len(selected) >= count:
                break
            if self.reserve_idea(preset_name=preset_slug, topic=topic, source="preset_pool"):
                selected.append(topic)

        # 3. If pool is exhausted or insufficient candidates remain:
        # Generate distinct unique topics with a serial angle so they are novel and distinct
        extra_needed = count - len(selected)
        if extra_needed > 0:
            preset_display = preset_slug.replace("_", " ").title()
            for i in range(1, 100):
                fallback_topic = f"{preset_display} Deep Dive Chapter {i}"
                if not self.is_idea_generated(fallback_topic):
                    if self.reserve_idea(preset_name=preset_slug, topic=fallback_topic, source="fallback_pool"):
                        selected.append(fallback_topic)
                        if len(selected) >= count:
                            break

        return selected

    def get_all_generated_ideas(self) -> List[Dict[str, Any]]:
        """Returns all generated ideas stored in SQLite."""
        try:
            rows = self.db.fetch_all_sync(
                "SELECT id, preset_name, topic, title, status, output_dir, created_at, completed_at FROM generated_ideas ORDER BY id DESC"
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Error fetching generated ideas: {e}")
            return []


# Global singleton instance
_global_idea_manager: Optional[IdeaManager] = None
_global_mgr_lock = threading.Lock()


def get_idea_manager(db_path: Optional[str] = None) -> IdeaManager:
    """Returns the shared application-wide IdeaManager instance."""
    global _global_idea_manager
    with _global_mgr_lock:
        if _global_idea_manager is None:
            db_coord = DatabaseCoordinator(db_path=db_path)
            _global_idea_manager = IdeaManager(db_coordinator=db_coord)
            _global_idea_manager.initialize()
        return _global_idea_manager
