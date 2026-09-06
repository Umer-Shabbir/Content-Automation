import os
_AUTOMATION_ROOT = Path(os.getenv('AUTOMATION_ROOT', Path(__file__).resolve().parents[2]))
_PRESETS_PATH = Path(os.getenv('MASTER_PRESETS_PATH', _AUTOMATION_ROOT / 'presets' / 'master_presets_registry.json'))
from pathlib import Path
import re

p = Path(_AUTOMATION_ROOT / 'Image Automation' / 'models.py')
content = p.read_text(encoding="utf-8")

# Let's replace the properties if needed, but since it already had it, we just want to expose the master presets loader

