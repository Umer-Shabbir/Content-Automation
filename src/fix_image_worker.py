import json
from pathlib import Path
import re

REGISTRY_PATH = Path('H:/Automation/Presets/master_presets_registry.json')
registry = json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))

p = Path("H:/Automation/Image Automation/worker.py")
content = p.read_text(encoding="utf-8")

# Make sure we don't try to print unicode that cp1252 can't handle
print(repr(content[:100]))

