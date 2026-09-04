import sys
import os
from pathlib import Path

# Add src/ directory to sys.path so 'app' and its submodules are discoverable everywhere
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure venv packages are usable across OSes if running with global Python
venv_candidates = [
    ROOT_DIR / "venv" / "Lib" / "site-packages",
    ROOT_DIR / ".venv" / "Lib" / "site-packages",
    *list((ROOT_DIR / "venv" / "lib").glob("python*/site-packages")),
    *list((ROOT_DIR / ".venv" / "lib").glob("python*/site-packages")),
]
for site_pkg in venv_candidates:
    if site_pkg.is_dir() and str(site_pkg) not in sys.path:
        sys.path.insert(0, str(site_pkg))

# Runtime self-healing: ensure essential folders exist
from app.core.config import ensure_runtime_dirs
ensure_runtime_dirs()

from app.ui.app import main

if __name__ == "__main__":
    main()
