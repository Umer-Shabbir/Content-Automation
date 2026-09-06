import os
_AUTOMATION_ROOT = Path(os.getenv('AUTOMATION_ROOT', Path(__file__).resolve().parents[2]))
_PRESETS_PATH = Path(os.getenv('MASTER_PRESETS_PATH', _AUTOMATION_ROOT / 'presets' / 'master_presets_registry.json'))
import json
from pathlib import Path
import re

REGISTRY_PATH = Path(_PRESETS_PATH)
registry = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))

p = Path(_AUTOMATION_ROOT / 'Image Automation' / 'worker.py')
content = p.read_text(encoding="utf-8")

# Make sure we don't try to print unicode that cp1252 can't handle
print(repr(content[:100]))

