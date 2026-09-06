import os
from pathlib import Path
_AUTOMATION_ROOT = Path(os.getenv('AUTOMATION_ROOT', Path(__file__).resolve().parents[2]))
_PRESETS_PATH = Path(os.getenv('MASTER_PRESETS_PATH', _AUTOMATION_ROOT / 'presets' / 'master_presets_registry.json'))
import re
with open(_AUTOMATION_ROOT / 'Video Forge' / 'app' / 'subtitles' / 'styler.py', "r", encoding="utf-8") as f:
    text = f.read()

# Fix broken ASS escaping from previous replace
text = text.replace("{\1c&H{spk_color}&}\b1{chunk.speaker}:\b0 ", "{\\1c&H{spk_color}&}\\b1{chunk.speaker}:\\b0 ")
text = text.replace("{\1c&H{chunk_normal_bbggrr}&}\b1{chunk.speaker}:\b0 ", "{\\1c&H{chunk_normal_bbggrr}&}\\b1{chunk.speaker}:\\b0 ")

with open(_AUTOMATION_ROOT / 'Video Forge' / 'app' / 'subtitles' / 'styler.py', "w", encoding="utf-8") as f:
    f.write(text)
