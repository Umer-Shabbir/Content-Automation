import os
from pathlib import Path
_AUTOMATION_ROOT = Path(os.getenv('AUTOMATION_ROOT', Path(__file__).resolve().parents[2]))
_PRESETS_PATH = Path(os.getenv('MASTER_PRESETS_PATH', _AUTOMATION_ROOT / 'presets' / 'master_presets_registry.json'))
import re
with open(_AUTOMATION_ROOT / 'Video Forge' / 'app' / 'subtitles' / 'styler.py', "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("text = f\"{\1c&H{spk_color}&}\b1{chunk.speaker}:\b0 {text}\"", "text = f\"{\\1c&H{spk_color}&}\\b1{chunk.speaker}:\\b0 {text}\"")

# Remove my old string
text = text.replace("spk_color = _ass_color_to_bbggrr(_get_speaker_color(chunk.speaker, profile))\n            text = f\"{\1c&H{spk_color}&}\b1{chunk.speaker}:\b0 {text}\"", "spk_color = _ass_color_to_bbggrr(_get_speaker_color(chunk.speaker, profile))\n            text = f\"{\\1c&H{spk_color}&}\\b1{chunk.speaker}:\\b0 {text}\"")

for sp_c in ["{\x01c", "\x081", "\x080"]:
    text = text.replace(sp_c, ("{\\1c" if "1c" in sp_c else ("\\b1" if "1" in sp_c else "\\b0")))

text = text.replace("{\1c&H{spk_color}&}\b1{chunk.speaker}:\b0 ", "{\\1c&H{spk_color}&}\\b1{chunk.speaker}:\\b0 ")

with open(_AUTOMATION_ROOT / 'Video Forge' / 'app' / 'subtitles' / 'styler.py', "w", encoding="utf-8") as f:
    f.write(text)
