import sys
import os
from pathlib import Path

# Add src/ directory to sys.path so 'app' and its submodules are discoverable everywhere
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure venv packages are usable if running with global Python
VENV_SITE_PACKAGES = ROOT_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(VENV_SITE_PACKAGES))

from app.ui.app import main

if __name__ == "__main__":
    main()
