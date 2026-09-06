import os
_AUTOMATION_ROOT = Path(os.getenv('AUTOMATION_ROOT', Path(__file__).resolve().parents[2]))
_PRESETS_PATH = Path(os.getenv('MASTER_PRESETS_PATH', _AUTOMATION_ROOT / 'presets' / 'master_presets_registry.json'))
from pathlib import Path

p = Path(_AUTOMATION_ROOT / 'Image Automation' / 'automator.py')
content = p.read_text(encoding="utf-8")

for i, line in enumerate(content.splitlines()):
    if "project.json" in line or "metadata.json" in line:
        print(f"{i}: {line}")

