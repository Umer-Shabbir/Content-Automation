import os
_AUTOMATION_ROOT = Path(os.getenv('AUTOMATION_ROOT', Path(__file__).resolve().parents[2]))
_PRESETS_PATH = Path(os.getenv('MASTER_PRESETS_PATH', _AUTOMATION_ROOT / 'presets' / 'master_presets_registry.json'))
from pathlib import Path

p = Path(_AUTOMATION_ROOT / 'Video Forge' / 'app' / 'subtitles' / 'styler.py')
content = p.read_text(encoding="utf-8")

if "from typing import" not in content:
    content = "from typing import Optional, List\n" + content
elif "Optional" not in content:
    content = content.replace("from typing import ", "from typing import Optional, ")
p.write_text(content, encoding="utf-8")
