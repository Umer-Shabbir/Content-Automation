import os
import sys
from pathlib import Path
from typing import List, Optional

# Project root: directory containing main.py and requirements.txt
PROJECT_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = Path(os.getenv("AUTOMATION_ROOT", PROJECT_ROOT.parent))


def load_env_file(dotenv_path: Optional[Path] = None) -> None:
    """
    Lightweight .env loader that does not crash if python-dotenv is absent.
    If python-dotenv is installed, delegates to it. Otherwise parses basic KEY=VALUE pairs.
    """
    if dotenv_path is None:
        dotenv_path = PROJECT_ROOT / ".env"

    if not dotenv_path.is_file():
        return

    # Try standard python-dotenv first
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=dotenv_path, override=False)
        return
    except ImportError:
        pass

    # Fallback parser for standard KEY=VALUE lines
    try:
        content = dotenv_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            # Do not overwrite existing environment variables
            if key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


# Automatically load .env on module import
load_env_file()


def get_default_output_dir() -> Path:
    """
    Returns the resolved output directory.
    Checks environment variable first, falls back to legacy workspace path if present,
    otherwise defaults to a portable 'output' directory inside the project root.
    """
    env_dir = os.getenv("CONTENT_AUTOMATION_OUTPUT_DIR") or os.getenv("OUTPUT_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    legacy_host_dir = (WORKSPACE_ROOT / "output").resolve()
    if legacy_host_dir.is_dir():
        return legacy_host_dir

    return (PROJECT_ROOT / "output").resolve()


def get_default_db_path() -> Path:
    """
    Returns the resolved SQLite database path.
    """
    env_db = os.getenv("DATABASE_PATH") or os.getenv("CONTENT_AUTOMATION_DB_PATH")
    if env_db:
        return Path(env_db).resolve()
    return (PROJECT_ROOT / "ideas.db").resolve()


def get_presets_registry_path() -> Path:
    """
    Locates the master presets registry JSON file.
    Checks env var, then project-bundled copy, then legacy workspace path.
    """
    env_path = os.getenv("MASTER_PRESETS_PATH")
    if env_path and Path(env_path).is_file():
        return Path(env_path).resolve()

    bundled = PROJECT_ROOT / "presets" / "master_presets_registry.json"
    if bundled.is_file():
        return bundled.resolve()

    legacy_path = (WORKSPACE_ROOT / "Presets" / "master_presets_registry.json").resolve()
    if legacy_path.is_file():
        return legacy_path

    return bundled.resolve()


def get_default_scan_roots() -> List[str]:
    """
    Returns existing directories to scan for historical ideas.
    Can be configured via IDEA_SCAN_DIRS (semicolon or comma separated).
    """
    env_dirs = os.getenv("IDEA_SCAN_DIRS")
    if env_dirs:
        dirs = []
        for d in re_split(env_dirs):
            if d.strip():
                dirs.append(d.strip())
        return dirs

    # Known fallback scan candidates (only included if they actually exist on disk)
    candidates = [
        WORKSPACE_ROOT / "Generated Content",
        WORKSPACE_ROOT / "Old GenCon",
        WORKSPACE_ROOT / "output",
        get_default_output_dir(),
    ]
    existing = []
    for cand in candidates:
        p = Path(cand)
        if p.is_dir() and str(p.resolve()) not in existing:
            existing.append(str(p.resolve()))
    return existing


def re_split(s: str) -> List[str]:
    import re
    return [part for part in re.split(r'[,;]', s) if part.strip()]


def ensure_runtime_dirs() -> None:
    """
    Runtime self-healing: ensures essential directories exist.
    """
    # 1. Output directory
    out_dir = get_default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 2. Database directory
    db_path = get_default_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 3. User settings directory
    settings_dir = Path.home() / ".content_automation"
    settings_dir.mkdir(parents=True, exist_ok=True)
